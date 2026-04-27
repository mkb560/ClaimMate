from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from ai.ingestion.vector_store import get_sessionmaker
from app.auth_core import create_access_token, hash_password, verify_password
from models.auth_orm import CaseInviteRow, CaseMembershipRow, UserRow


def _utcnow() -> datetime:
    return datetime.now(UTC)


def hash_invite_token(plain: str) -> str:
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()


async def register_user(*, email: str, password: str, display_name: str | None) -> UserRow:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        row = UserRow(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            display_name=display_name.strip() if display_name else None,
            created_at=now,
        )
        session.add(row)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ValueError("Email already registered.") from exc
        await session.refresh(row)
        return row


async def authenticate_user(*, email: str, password: str) -> UserRow | None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = select(UserRow).where(UserRow.email == email.strip().lower())
        result = await session.scalars(stmt)
        row = result.first()
        if row is None:
            return None
        if not verify_password(password, row.password_hash):
            return None
        return row


async def get_user_by_id(user_id: uuid.UUID) -> UserRow | None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        return await session.get(UserRow, user_id)


async def count_case_members(case_id: str) -> int:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = select(func.count()).select_from(CaseMembershipRow).where(CaseMembershipRow.case_id == case_id)
        n = await session.scalar(stmt)
        return int(n or 0)


async def get_membership(case_id: str, user_id: uuid.UUID) -> CaseMembershipRow | None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = select(CaseMembershipRow).where(
            CaseMembershipRow.case_id == case_id,
            CaseMembershipRow.user_id == user_id,
        )
        result = await session.scalars(stmt)
        return result.first()


async def is_case_member(case_id: str, user_id: uuid.UUID) -> bool:
    return await get_membership(case_id, user_id) is not None


async def list_case_members(case_id: str) -> list[dict[str, Any]]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = (
            select(CaseMembershipRow)
            .where(CaseMembershipRow.case_id == case_id)
            .order_by(CaseMembershipRow.role.asc())
        )
        result = await session.scalars(stmt)
        rows = result.all()
    return [
        {
            "user_id": str(row.user_id),
            "role": row.role,
        }
        for row in rows
    ]


async def add_case_member(case_id: str, user_id: uuid.UUID, role: str) -> CaseMembershipRow:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        row = CaseMembershipRow(case_id=case_id, user_id=user_id, role=role)
        session.add(row)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise ValueError("User is already a member of this case.") from exc
        await session.refresh(row)
        return row


async def add_case_owner_if_absent(case_id: str, user_id: uuid.UUID) -> None:
    if await get_membership(case_id, user_id) is not None:
        return
    if await count_case_members(case_id) > 0:
        return
    await add_case_member(case_id, user_id, "owner")


async def create_case_invite(
    *,
    case_id: str,
    created_by_user_id: uuid.UUID,
    role: str = "member",
    expires_in_hours: int = 24 * 7,
) -> tuple[str, CaseInviteRow]:
    existing = await get_membership(case_id, created_by_user_id)
    if existing is None or existing.role != "owner":
        raise PermissionError("Only the case owner can create invites.")

    plain = secrets.token_urlsafe(32)
    token_hash = hash_invite_token(plain)
    now = _utcnow()
    expires_at = now + timedelta(hours=max(1, min(expires_in_hours, 24 * 30)))

    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        row = CaseInviteRow(
            case_id=case_id,
            token_hash=token_hash,
            role=role,
            expires_at=expires_at,
            created_by_user_id=created_by_user_id,
            created_at=now,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return plain, row


async def lookup_invite(plain_token: str) -> dict[str, Any] | None:
    sessionmaker = get_sessionmaker()
    th = hash_invite_token(plain_token.strip())
    now = _utcnow()
    async with sessionmaker() as session:
        stmt = select(CaseInviteRow).where(CaseInviteRow.token_hash == th)
        result = await session.scalars(stmt)
        row = result.first()
        if row is None:
            return None
        valid = row.expires_at >= now
        return {
            "case_id": row.case_id,
            "role": row.role,
            "expires_at": row.expires_at.isoformat(),
            "valid": valid,
        }


async def accept_invite(*, user_id: uuid.UUID, plain_token: str) -> str:
    sessionmaker = get_sessionmaker()
    th = hash_invite_token(plain_token.strip())
    now = _utcnow()
    async with sessionmaker() as session:
        stmt = select(CaseInviteRow).where(CaseInviteRow.token_hash == th)
        result = await session.scalars(stmt)
        inv = result.first()
        if inv is None:
            raise ValueError("Invite not found.")
        if inv.expires_at < now:
            await session.delete(inv)
            await session.commit()
            raise ValueError("Invite has expired.")
        case_id = inv.case_id
        role = inv.role
        mres = await session.scalars(
            select(CaseMembershipRow).where(
                CaseMembershipRow.case_id == case_id,
                CaseMembershipRow.user_id == user_id,
            )
        )
        existing = mres.first()
        if existing is None:
            session.add(CaseMembershipRow(case_id=case_id, user_id=user_id, role=role))
        await session.delete(inv)
        await session.commit()
    return case_id


async def delete_memberships_and_invites_for_case(case_id: str) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(delete(CaseMembershipRow).where(CaseMembershipRow.case_id == case_id))
        await session.execute(delete(CaseInviteRow).where(CaseInviteRow.case_id == case_id))
        await session.commit()


def user_to_public(row: UserRow) -> dict[str, Any]:
    return {
        "user_id": str(row.id),
        "email": row.email,
        "display_name": row.display_name,
        "created_at": row.created_at.isoformat(),
    }


def issue_token_for_user(user: UserRow) -> str:
    return create_access_token(subject_user_id=str(user.id))

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.accident.report_payload_builder import build_accident_chat_context, build_accident_report_payload
from ai.ingestion.vector_store import get_sessionmaker, replace_case_chunks
from app.accident_codec import _jsonable, deep_merge, stage_a_from_dict, stage_b_from_dict
from models.auth_orm import CaseMembershipRow
from models.case_orm import CaseChatMessageRow, CaseRow, generate_case_id


def _utcnow() -> datetime:
    return datetime.now(UTC)


async def create_case(*, case_id: str | None = None) -> str:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    resolved_id = case_id or generate_case_id()
    async with sessionmaker() as session:
        existing = await session.get(CaseRow, resolved_id)
        if existing is not None:
            raise ValueError(f"case_id already exists: {resolved_id}")
        row = CaseRow(
            id=resolved_id,
            stage_a_json={},
            stage_b_json=None,
            report_payload_json=None,
            chat_context_json=None,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        await session.commit()
    return resolved_id


async def ensure_case(case_id: str) -> None:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        row = await session.get(CaseRow, case_id)
        if row is None:
            session.add(
                CaseRow(
                    id=case_id,
                    stage_a_json={},
                    stage_b_json=None,
                    report_payload_json=None,
                    chat_context_json=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            await session.commit()
        return


async def get_case_row(case_id: str) -> CaseRow | None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        return await session.get(CaseRow, case_id)


def serialize_case_snapshot(row: CaseRow) -> dict[str, Any]:
    chat_ctx = row.chat_context_json
    room_bootstrap: dict[str, Any] | None = None
    if isinstance(chat_ctx, dict) and chat_ctx:
        room_bootstrap = {
            "pinned_document_title": chat_ctx.get("pinned_document_title"),
            "summary": chat_ctx.get("summary"),
            "key_facts": chat_ctx.get("key_facts") or [],
            "follow_up_items": chat_ctx.get("follow_up_items") or [],
            "party_comparison_rows": chat_ctx.get("party_comparison_rows") or [],
            "generated_at": chat_ctx.get("generated_at"),
        }
    return {
        "case_id": row.id,
        "claim_notice_at": _jsonable(row.claim_notice_at),
        "proof_of_claim_at": _jsonable(row.proof_of_claim_at),
        "last_deadline_alert_at": _jsonable(row.last_deadline_alert_at),
        "stage_a": dict(row.stage_a_json or {}),
        "stage_b": row.stage_b_json,
        "report_payload": row.report_payload_json,
        "chat_context": row.chat_context_json,
        "room_bootstrap": room_bootstrap,
        "created_at": _jsonable(row.created_at),
        "updated_at": _jsonable(row.updated_at),
    }


async def patch_stage_a(case_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        row = await _require_case(session, case_id)
        merged = deep_merge(dict(row.stage_a_json or {}), patch)
        row.stage_a_json = merged
        row.updated_at = now
        await session.commit()
    return merged


async def patch_stage_b(case_id: str, patch: dict[str, Any]) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        row = await _require_case(session, case_id)
        base = dict(row.stage_b_json or {})
        merged = deep_merge(base, patch)
        row.stage_b_json = merged
        row.updated_at = now
        await session.commit()
    return merged


async def append_stage_a_photo_attachment(case_id: str, attachment: dict[str, Any]) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        row = await _require_case(session, case_id)
        stage_a = dict(row.stage_a_json or {})
        existing = stage_a.get("photo_attachments")
        if isinstance(existing, list):
            attachments = [item for item in existing if isinstance(item, dict)]
        else:
            attachments = []
        attachments.append(attachment)
        stage_a["photo_attachments"] = attachments
        row.stage_a_json = stage_a
        row.updated_at = now
        await session.commit()
    return stage_a


async def _require_case(session: AsyncSession, case_id: str) -> CaseRow:
    row = await session.get(CaseRow, case_id)
    if row is None:
        raise KeyError(case_id)
    return row


async def update_claim_dates(
    case_id: str,
    *,
    claim_notice_at: datetime | None,
    proof_of_claim_at: datetime | None,
) -> None:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        row = await _require_case(session, case_id)
        row.claim_notice_at = claim_notice_at
        row.proof_of_claim_at = proof_of_claim_at
        row.last_deadline_alert_at = None
        row.updated_at = now
        await session.commit()


async def generate_and_store_report(case_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        row = await _require_case(session, case_id)
        stage_a = stage_a_from_dict(row.stage_a_json or {})
        stage_b = stage_b_from_dict(row.stage_b_json)
        payload = build_accident_report_payload(case_id, stage_a, stage_b)
        chat_ctx = build_accident_chat_context(payload)
        payload_dict = _jsonable(payload)
        chat_dict = _jsonable(chat_ctx)
        row.report_payload_json = payload_dict
        row.chat_context_json = chat_dict
        row.updated_at = now
        await session.commit()
    return payload_dict, chat_dict


async def get_stored_report(case_id: str) -> dict[str, Any] | None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        row = await session.get(CaseRow, case_id)
        if row is None:
            return None
        return row.report_payload_json


async def get_stored_chat_context(case_id: str) -> dict[str, Any] | None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        row = await session.get(CaseRow, case_id)
        if row is None:
            return None
        return row.chat_context_json


def _serialize_chat_message_row(row: CaseChatMessageRow) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "case_id": row.case_id,
        "sender_role": row.sender_role,
        "message_type": row.message_type,
        "body_text": row.body_text,
        "ai_payload": row.ai_payload,
        "metadata": row.metadata_json,
        "created_at": _jsonable(row.created_at),
    }


async def append_chat_user_message(
    case_id: str,
    sender_role: str,
    message_text: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    async with sessionmaker() as session:
        await _require_case(session, case_id)
        row = CaseChatMessageRow(
            case_id=case_id,
            sender_role=sender_role,
            message_type="user",
            body_text=message_text,
            ai_payload=None,
            metadata_json=metadata,
            created_at=now,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return _serialize_chat_message_row(row)


async def append_chat_ai_message(case_id: str, ai_payload: dict[str, Any]) -> dict[str, Any]:
    sessionmaker = get_sessionmaker()
    now = _utcnow()
    text = str(ai_payload.get("text") or "")
    async with sessionmaker() as session:
        await _require_case(session, case_id)
        row = CaseChatMessageRow(
            case_id=case_id,
            sender_role="assistant",
            message_type="ai",
            body_text=text,
            ai_payload=ai_payload,
            metadata_json=None,
            created_at=now,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
    return _serialize_chat_message_row(row)


async def list_chat_messages(case_id: str, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    sessionmaker = get_sessionmaker()
    cap = min(max(limit, 1), 500)
    off = max(offset, 0)
    async with sessionmaker() as session:
        stmt = (
            select(CaseChatMessageRow)
            .where(CaseChatMessageRow.case_id == case_id)
            .order_by(CaseChatMessageRow.created_at.asc())
            .offset(off)
            .limit(cap)
        )
        result = await session.scalars(stmt)
        rows = result.all()
    return [_serialize_chat_message_row(r) for r in rows]


async def list_user_cases(user_id: uuid.UUID) -> list[dict[str, Any]]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = (
            select(CaseMembershipRow, CaseRow)
            .join(CaseRow, CaseMembershipRow.case_id == CaseRow.id)
            .where(CaseMembershipRow.user_id == user_id)
            .order_by(CaseRow.created_at.desc())
        )
        result = await session.execute(stmt)
        rows = result.all()
    return [
        {
            "case_id": membership.case_id,
            "role": membership.role,
            "created_at": _jsonable(case_row.created_at),
        }
        for membership, case_row in rows
    ]


async def delete_case_and_related_data(case_id: str) -> bool:
    from app.auth_service import delete_memberships_and_invites_for_case

    await delete_memberships_and_invites_for_case(case_id)
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(delete(CaseChatMessageRow).where(CaseChatMessageRow.case_id == case_id))
        row = await session.get(CaseRow, case_id)
        if row is None:
            await session.commit()
            return False
        await session.delete(row)
        await session.commit()
    await replace_case_chunks(case_id, [])
    return True

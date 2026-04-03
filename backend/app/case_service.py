from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ai.accident.report_payload_builder import build_accident_chat_context, build_accident_report_payload
from ai.ingestion.vector_store import get_sessionmaker
from app.accident_codec import _jsonable, deep_merge, stage_a_from_dict, stage_b_from_dict
from models.case_orm import CaseRow, generate_case_id


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

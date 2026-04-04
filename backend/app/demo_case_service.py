from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAIError

from ai.chat.chat_ai_service import handle_chat_event
from ai.ingestion.kb_b_loader import build_local_kb_b_sources, index_kb_b_sources
from ai.ingestion.vector_store import list_kb_b_chunks
from app import case_service
from app.chat_serialize import ai_response_to_dict
from app.demo_seed_data import (
    DEMO_ACCIDENT_CASE_ID,
    build_demo_chat_event_payloads,
    build_demo_claim_dates_payload,
    build_demo_stage_a_payload,
    build_demo_stage_b_payload,
)
from models.ai_types import ChatEvent, ChatEventTrigger, Participant

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


async def ensure_demo_kb_b_ready(*, allow_index: bool = True) -> str:
    if await list_kb_b_chunks(limit=1):
        return "existing"
    if not allow_index:
        return "missing"
    docs_dir = REPO_ROOT / "claimmate_rag_docs"
    sources = build_local_kb_b_sources(docs_dir)
    if not sources:
        return "missing"
    await index_kb_b_sources(sources)
    return "indexed"


def _to_chat_event(payload: dict[str, Any]) -> ChatEvent:
    return ChatEvent(
        case_id=payload["case_id"],
        sender_role=payload["sender_role"],
        message_text=payload["message_text"],
        participants=[Participant(user_id=item["user_id"], role=item["role"]) for item in payload["participants"]],
        invite_sent=payload["invite_sent"],
        trigger=ChatEventTrigger(payload["trigger"]),
        metadata=payload.get("metadata", {}),
    )


async def seed_demo_accident_case(
    case_id: str = DEMO_ACCIDENT_CASE_ID,
    *,
    allow_index_kb_b: bool = True,
) -> dict[str, Any]:
    stage_a = build_demo_stage_a_payload()
    stage_b = build_demo_stage_b_payload()
    claim_dates = build_demo_claim_dates_payload()
    chat_events = build_demo_chat_event_payloads(case_id)

    kb_b_status = await ensure_demo_kb_b_ready(allow_index=allow_index_kb_b)
    await case_service.ensure_case(case_id)
    await case_service.patch_stage_a(case_id, stage_a)
    await case_service.patch_stage_b(case_id, stage_b)
    await case_service.update_claim_dates(
        case_id,
        claim_notice_at=_parse_dt(claim_dates["claim_notice_at"]),
        proof_of_claim_at=_parse_dt(claim_dates["proof_of_claim_at"]),
    )
    report_payload, chat_context = await case_service.generate_and_store_report(case_id)

    chat_responses: dict[str, Any] = {}
    chat_errors: dict[str, str] = {}
    for label, payload in chat_events.items():
        try:
            response = await handle_chat_event(_to_chat_event(payload))
        except OpenAIError as exc:
            chat_errors[label] = str(exc)
            continue
        chat_responses[label] = None if response is None else ai_response_to_dict(response)

    row = await case_service.get_case_row(case_id)
    return {
        "case_id": case_id,
        "kb_b_status": kb_b_status,
        "stage_a": stage_a,
        "stage_b": stage_b,
        "claim_dates": claim_dates,
        "report_payload": report_payload,
        "chat_context": chat_context,
        "sample_chat_requests": chat_events,
        "sample_chat_responses": chat_responses,
        "sample_chat_errors": chat_errors,
        "case_snapshot": case_service.serialize_case_snapshot(row) if row is not None else None,
    }

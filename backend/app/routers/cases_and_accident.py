from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request
from pydantic import BaseModel, Field

from ai.chat.chat_ai_service import handle_chat_event
from app.case_validation import validate_case_id
from app.chat_serialize import ai_response_to_dict
from app.demo_case_service import seed_demo_accident_case
from app.deps import ensure_ai_ready, ensure_db_ready
from app import case_service
from models.ai_types import ChatEvent, ChatEventTrigger, Participant

router = APIRouter(tags=["cases"])


class CreateCaseBody(BaseModel):
    case_id: str | None = Field(default=None, max_length=64)


class ClaimDatesBody(BaseModel):
    claim_notice_at: datetime | None = None
    proof_of_claim_at: datetime | None = None


class ParticipantIn(BaseModel):
    user_id: str
    role: str


class ChatEventBody(BaseModel):
    sender_role: str
    message_text: str = ""
    participants: list[ParticipantIn]
    invite_sent: bool
    trigger: ChatEventTrigger
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


@router.post("/cases", status_code=201)
async def create_case(request: Request, body: CreateCaseBody = CreateCaseBody()) -> dict[str, str]:
    ensure_db_ready(request)
    requested_id = None
    if body.case_id is not None and body.case_id.strip():
        requested_id = validate_case_id(body.case_id.strip())
    try:
        case_id = await case_service.create_case(case_id=requested_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"case_id": case_id}


@router.get("/cases/{case_id}")
async def get_case_snapshot(case_id: str, request: Request) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return case_service.serialize_case_snapshot(row)


@router.post("/cases/{case_id}/demo/seed-accident")
async def seed_accident_demo_case(case_id: str, request: Request) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    return await seed_demo_accident_case(normalized)


@router.patch("/cases/{case_id}/accident/stage-a")
async def accident_stage_a(
    case_id: str,
    request: Request,
    patch: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    try:
        merged = await case_service.patch_stage_a(normalized, patch)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found.") from exc
    return {"case_id": normalized, "stage_a": merged}


@router.patch("/cases/{case_id}/accident/stage-b")
async def accident_stage_b(
    case_id: str,
    request: Request,
    patch: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    try:
        merged = await case_service.patch_stage_b(normalized, patch)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found.") from exc
    return {"case_id": normalized, "stage_b": merged}


@router.post("/cases/{case_id}/accident/report")
async def generate_accident_report(case_id: str, request: Request) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    try:
        payload, chat_context = await case_service.generate_and_store_report(normalized)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found.") from exc
    return {
        "case_id": normalized,
        "report_payload": payload,
        "chat_context": chat_context,
    }


@router.get("/cases/{case_id}/accident/report")
async def get_accident_report(case_id: str, request: Request) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    stored = await case_service.get_stored_report(normalized)
    if stored is None:
        row = await case_service.get_case_row(normalized)
        if row is None:
            raise HTTPException(status_code=404, detail="Case not found.")
        raise HTTPException(status_code=404, detail="Accident report has not been generated yet.")
    chat = await case_service.get_stored_chat_context(normalized)
    return {"case_id": normalized, "report_payload": stored, "chat_context": chat}


@router.patch("/cases/{case_id}/claim-dates")
async def patch_claim_dates(case_id: str, request: Request, body: ClaimDatesBody) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    try:
        await case_service.update_claim_dates(
            normalized,
            claim_notice_at=body.claim_notice_at,
            proof_of_claim_at=body.proof_of_claim_at,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found.") from exc
    return {
        "case_id": normalized,
        "claim_notice_at": body.claim_notice_at,
        "proof_of_claim_at": body.proof_of_claim_at,
    }


@router.post("/cases/{case_id}/chat/event")
async def chat_event(case_id: str, request: Request, body: ChatEventBody) -> dict[str, object]:
    ensure_ai_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")

    event = ChatEvent(
        case_id=normalized,
        sender_role=body.sender_role,
        message_text=body.message_text,
        participants=[Participant(user_id=p.user_id, role=p.role) for p in body.participants],
        invite_sent=body.invite_sent,
        trigger=body.trigger,
        metadata=body.metadata,
        occurred_at=body.occurred_at,
    )
    response = await handle_chat_event(event)
    if response is None:
        return {"case_id": normalized, "response": None}
    return {"case_id": normalized, "response": ai_response_to_dict(response)}

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from app.auth_deps import AuthContext, get_auth_context
from app.auth_service import add_case_owner_if_absent
from app.case_access import assert_can_access_case, assert_can_create_case
from app.case_validation import validate_case_id
from app.chat_dispatch import chat_event_dispatch
from app.demo_case_service import seed_demo_accident_case
from app.deps import ensure_ai_ready, ensure_db_ready
from app import case_service
from models.ai_types import ChatEventTrigger, Participant

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


class ChatMessageSimpleBody(BaseModel):
    """Lou-friendly POST: default participants = single owner (stage 1). Use @AI in message_text for mentions."""

    message_text: str = Field(min_length=1, max_length=8000)
    sender_role: str = "owner"
    invite_sent: bool = False
    participants: list[ParticipantIn] | None = None


@router.get("/cases")
async def list_cases(
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    if ctx.user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    cases = await case_service.list_user_cases(ctx.user.id)
    return {"cases": cases}


@router.post("/cases", status_code=201)
async def create_case(
    request: Request,
    body: CreateCaseBody = CreateCaseBody(),
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, str]:
    ensure_db_ready(request)
    await assert_can_create_case(ctx)
    requested_id = None
    if body.case_id is not None and body.case_id.strip():
        requested_id = validate_case_id(body.case_id.strip())
    try:
        case_id = await case_service.create_case(case_id=requested_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if ctx.user is not None:
        await add_case_owner_if_absent(case_id, ctx.user.id)
    return {"case_id": case_id}


@router.get("/cases/{case_id}")
async def get_case_snapshot(
    case_id: str,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
    return case_service.serialize_case_snapshot(row)


@router.post("/cases/{case_id}/demo/seed-accident")
async def seed_accident_demo_case(
    case_id: str,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    await assert_can_access_case(normalized, ctx)
    return await seed_demo_accident_case(normalized)


@router.patch("/cases/{case_id}/accident/stage-a")
async def accident_stage_a(
    case_id: str,
    request: Request,
    patch: dict[str, Any] = Body(default_factory=dict),
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
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
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
    try:
        merged = await case_service.patch_stage_b(normalized, patch)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Case not found.") from exc
    return {"case_id": normalized, "stage_b": merged}


@router.post("/cases/{case_id}/accident/report")
async def generate_accident_report(
    case_id: str,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
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
async def get_accident_report(
    case_id: str,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
    stored = await case_service.get_stored_report(normalized)
    if stored is None:
        raise HTTPException(status_code=404, detail="Accident report has not been generated yet.")
    chat = await case_service.get_stored_chat_context(normalized)
    return {"case_id": normalized, "report_payload": stored, "chat_context": chat}


@router.patch("/cases/{case_id}/claim-dates")
async def patch_claim_dates(
    case_id: str,
    request: Request,
    body: ClaimDatesBody,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
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


@router.get("/cases/{case_id}/chat/messages")
async def list_case_chat_messages(
    case_id: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
    messages = await case_service.list_chat_messages(normalized, limit=limit, offset=offset)
    return {"case_id": normalized, "messages": messages, "limit": limit, "offset": offset}


@router.post("/cases/{case_id}/chat/messages")
async def post_case_chat_message(
    case_id: str,
    request: Request,
    body: ChatMessageSimpleBody,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_ai_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
    parts = body.participants or [ParticipantIn(user_id="owner-1", role="owner")]
    participants = [Participant(user_id=p.user_id, role=p.role) for p in parts]
    result = await chat_event_dispatch(
        normalized,
        sender_role=body.sender_role,
        message_text=body.message_text.strip(),
        participants=participants,
        invite_sent=body.invite_sent,
        trigger=ChatEventTrigger.MESSAGE,
        metadata={"source": "post_chat_messages", "direct_ai_chat": True},
        occurred_at=None,
    )
    return {"case_id": normalized, "response": result}


@router.post("/cases/{case_id}/chat/event")
async def chat_event(
    case_id: str,
    request: Request,
    body: ChatEventBody,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_ai_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)

    result = await chat_event_dispatch(
        normalized,
        sender_role=body.sender_role,
        message_text=body.message_text,
        participants=[Participant(user_id=p.user_id, role=p.role) for p in body.participants],
        invite_sent=body.invite_sent,
        trigger=body.trigger,
        metadata=body.metadata,
        occurred_at=body.occurred_at,
    )
    return {"case_id": normalized, "response": result}


@router.delete("/cases/{case_id}", status_code=204)
async def delete_case_endpoint(
    case_id: str,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
) -> Response:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
    deleted = await case_service.delete_case_and_related_data(normalized)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found.")
    return Response(status_code=204)

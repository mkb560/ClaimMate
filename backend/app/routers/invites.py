from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.auth_deps import AuthContext, get_auth_context
from app.auth_service import accept_invite, create_case_invite, lookup_invite
from app.case_access import assert_can_access_case
from app.case_validation import validate_case_id
from app.deps import ensure_db_ready
from app import case_service
from pydantic import BaseModel, Field

router = APIRouter(tags=["invites"])


class CreateInviteBody(BaseModel):
    role: str = Field(default="member", max_length=32)
    expires_in_hours: int = Field(default=24 * 7, ge=1, le=24 * 30)


class AcceptInviteBody(BaseModel):
    token: str = Field(min_length=8, max_length=512)


@router.post("/cases/{case_id}/invites")
async def create_invite_for_case(
    case_id: str,
    request: Request,
    body: CreateInviteBody = CreateInviteBody(),
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized, ctx)
    if ctx.user is None:
        raise HTTPException(status_code=401, detail="Authentication required to create invites.")
    try:
        plain, inv = await create_case_invite(
            case_id=normalized,
            created_by_user_id=ctx.user.id,
            role=body.role,
            expires_in_hours=body.expires_in_hours,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return {
        "case_id": normalized,
        "token": plain,
        "invite_id": str(inv.id),
        "role": inv.role,
        "expires_at": inv.expires_at.isoformat(),
    }


@router.get("/invites/lookup")
async def lookup_invite_token(request: Request, token: str = Query(..., min_length=8)) -> dict[str, object]:
    ensure_db_ready(request)
    info = await lookup_invite(token)
    if info is None:
        raise HTTPException(status_code=404, detail="Invite not found.")
    return info


@router.post("/auth/accept-invite")
async def accept_invite_route(
    request: Request,
    body: AcceptInviteBody,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    if ctx.user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        case_id = await accept_invite(user_id=ctx.user.id, plain_token=body.token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"case_id": case_id, "accepted": True}

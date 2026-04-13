from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, WebSocket
from starlette.websockets import WebSocketDisconnect

from ai.config import ai_config
from app.auth_core import decode_access_token
from app.auth_deps import AuthContext
from app.auth_service import get_user_by_id
from app.case_access import assert_can_access_case
from app.case_validation import validate_case_id
from app.chat_dispatch import chat_event_dispatch
from app import case_service
from app.ws_room_manager import case_room_manager
from models.ai_types import ChatEventTrigger, Participant

router = APIRouter(tags=["websocket"])


def _normalize_mode() -> str:
    m = (ai_config.auth_mode or "off").strip().lower()
    if m not in ("off", "optional", "required"):
        return "off"
    return m


async def _auth_ctx_from_token(token: str | None) -> AuthContext | None:
    """Returns None if the client must be rejected before ``connect`` (bad JWT)."""
    mode = _normalize_mode()
    if not token or not token.strip():
        return AuthContext(mode=mode, user=None)
    if not ai_config.jwt_secret_key.strip():
        return None
    try:
        claims = decode_access_token(token.strip())
    except Exception:
        return None
    sub = claims.get("sub")
    if not sub or not isinstance(sub, str):
        return None
    try:
        uid = UUID(sub)
    except ValueError:
        return None
    user = await get_user_by_id(uid)
    if user is None:
        return None
    return AuthContext(mode=mode, user=user)


@router.websocket("/ws/cases/{case_id}")
async def case_chat_websocket(
    websocket: WebSocket,
    case_id: str,
    token: str | None = Query(default=None),
) -> None:
    """Realtime room for a case: relay messages and optional AI dispatch.

    Send JSON: ``{"type":"chat","message_text":"...","sender_role":"owner","invite_sent":false,"run_ai":true}``.
    JWT: ``?token=...`` query parameter (same claims as HTTP Bearer).
    """
    normalized = validate_case_id(case_id)
    ctx = await _auth_ctx_from_token(token)
    if ctx is None:
        await websocket.close(code=4401)
        return

    row = await case_service.get_case_row(normalized)
    if row is None:
        await websocket.close(code=4404)
        return
    try:
        await assert_can_access_case(normalized, ctx)
    except HTTPException as exc:
        await websocket.close(code=4403 if exc.status_code == 403 else 4401)
        return

    await case_room_manager.connect(normalized, websocket)
    client_id = str(id(websocket))
    await case_room_manager.broadcast_json(
        normalized,
        {"type": "system", "event": "join", "case_id": normalized, "client_id": client_id},
        exclude=websocket,
    )
    try:
        await websocket.send_text(
            json.dumps({"type": "ready", "case_id": normalized, "client_id": client_id}, default=str)
        )
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            try:
                payload: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "detail": "invalid_json"}))
                continue
            msg_type = payload.get("type")
            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                continue
            if msg_type == "chat":
                text = str(payload.get("message_text") or "").strip()
                sender_role = str(payload.get("sender_role") or "owner")
                invite_sent = bool(payload.get("invite_sent", False))
                raw_parts = payload.get("participants")
                if isinstance(raw_parts, list) and raw_parts:
                    participants = [
                        Participant(user_id=str(p.get("user_id", "owner-1")), role=str(p.get("role", "owner")))
                        for p in raw_parts
                        if isinstance(p, dict)
                    ]
                else:
                    participants = [Participant(user_id="owner-1", role="owner")]
                run_ai = bool(payload.get("run_ai", True))
                out_event = {
                    "type": "user_message",
                    "case_id": normalized,
                    "sender_role": sender_role,
                    "message_text": text,
                    "client_id": client_id,
                }
                await case_room_manager.broadcast_json(normalized, out_event)
                if not text:
                    continue
                if run_ai:
                    try:
                        ai_payload = await chat_event_dispatch(
                            normalized,
                            sender_role=sender_role,
                            message_text=text,
                            participants=participants,
                            invite_sent=invite_sent,
                            trigger=ChatEventTrigger.MESSAGE,
                            metadata={"source": "websocket"},
                            occurred_at=None,
                        )
                    except Exception as exc:
                        await websocket.send_text(
                            json.dumps({"type": "error", "detail": "ai_dispatch_failed", "message": str(exc)})
                        )
                        continue
                    if ai_payload is not None:
                        await case_room_manager.broadcast_json(
                            normalized,
                            {
                                "type": "ai_message",
                                "case_id": normalized,
                                "payload": ai_payload,
                                "client_id": client_id,
                            },
                        )
                continue
            await websocket.send_text(json.dumps({"type": "error", "detail": "unknown_type", "seen": msg_type}))
    finally:
        case_room_manager.disconnect(normalized, websocket)
        await case_room_manager.broadcast_json(
            normalized,
            {"type": "system", "event": "leave", "case_id": normalized, "client_id": client_id},
        )

from __future__ import annotations

from datetime import datetime
from typing import Any

from ai.chat.chat_ai_service import handle_chat_event
from app import case_service
from app.chat_serialize import ai_response_to_dict
from models.ai_types import ChatEvent, ChatEventTrigger, Participant


async def chat_event_dispatch(
    case_id: str,
    *,
    sender_role: str,
    message_text: str,
    participants: list[Participant],
    invite_sent: bool,
    trigger: ChatEventTrigger,
    metadata: dict[str, Any],
    occurred_at: datetime | None = None,
) -> dict[str, Any] | None:
    event = ChatEvent(
        case_id=case_id,
        sender_role=sender_role,
        message_text=message_text,
        participants=participants,
        invite_sent=invite_sent,
        trigger=trigger,
        metadata=dict(metadata),
        occurred_at=occurred_at,
    )
    if trigger == ChatEventTrigger.MESSAGE and message_text.strip():
        merged_meta = dict(metadata)
        merged_meta.setdefault("chat_event_trigger", trigger.value)
        await case_service.append_chat_user_message(
            case_id,
            sender_role,
            message_text.strip(),
            metadata=merged_meta,
        )
    response = await handle_chat_event(event)
    if response is None:
        return None
    payload = ai_response_to_dict(response)
    await case_service.append_chat_ai_message(case_id, payload)
    return payload

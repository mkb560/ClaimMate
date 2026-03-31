from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class ChatStage(StrEnum):
    STAGE_1 = "stage_1"
    STAGE_2 = "stage_2"
    STAGE_3 = "stage_3"


class AITrigger(StrEnum):
    DISPUTE = "DISPUTE"
    MENTION = "MENTION"
    PROACTIVE = "PROACTIVE"
    DEADLINE = "DEADLINE"


class ChatEventTrigger(StrEnum):
    MESSAGE = "MESSAGE"
    PARTICIPANT_JOINED = "PARTICIPANT_JOINED"
    POLICY_INDEXED = "POLICY_INDEXED"


@dataclass(slots=True)
class Participant:
    user_id: str
    role: str


@dataclass(slots=True)
class Citation:
    source_type: str
    source_label: str
    document_id: str
    page_num: int | None = None
    section: str | None = None
    excerpt: str = ""


@dataclass(slots=True)
class AnswerResponse:
    answer: str
    citations: list[Citation]
    disclaimer: str


@dataclass(slots=True)
class AIResponse:
    text: str
    citations: list[Citation]
    trigger: AITrigger
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ChatEvent:
    case_id: str
    sender_role: str
    message_text: str
    participants: list[Participant]
    invite_sent: bool
    trigger: ChatEventTrigger
    metadata: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime | None = None

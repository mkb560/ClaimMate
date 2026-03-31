from __future__ import annotations

from models.ai_types import ChatStage, Participant


def determine_stage(participants: list[Participant], invite_sent: bool) -> ChatStage:
    roles = {participant.role for participant in participants}
    has_external = "adjuster" in roles or "repair_shop" in roles

    if has_external:
        return ChatStage.STAGE_3
    if invite_sent:
        return ChatStage.STAGE_2
    return ChatStage.STAGE_1


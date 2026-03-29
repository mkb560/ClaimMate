from __future__ import annotations

from models.ai_types import ChatStage


def build_stage_instruction(stage: ChatStage) -> str:
    if stage == ChatStage.STAGE_1:
        return "You are speaking only to the case owner. Be direct, educational, and easy to follow."
    if stage == ChatStage.STAGE_2:
        return "You are still speaking only to the owner, but they are preparing to involve an adjuster or repair shop. Prioritize document readiness and timelines."
    return "Multiple parties may read this answer. Keep the tone neutral and factual. Avoid advocacy language."


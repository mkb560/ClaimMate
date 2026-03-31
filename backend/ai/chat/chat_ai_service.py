from __future__ import annotations

from ai.chat.mention_handler import contains_ai_mention, extract_ai_question
from ai.chat.stage_prompts import build_stage_instruction
from ai.chat.stage_router import determine_stage
from ai.deadline.deadline_checker import maybe_get_deadline_alert
from ai.dispute.keyword_filter import detect_dispute_signal
from ai.dispute.semantic_detector import classify_dispute
from ai.rag.prompt_templates import DISCLAIMER_FOOTER
from ai.rag.query_engine import answer_dispute_question, answer_policy_question, summarize_policy_highlights
from models.ai_types import AIResponse, AITrigger, ChatEvent, ChatEventTrigger, ChatStage


def _prefix_for_reference(text: str) -> str:
    cleaned = text.replace(DISCLAIMER_FOOTER, "").strip()
    return f"For reference: {cleaned}\n\n{DISCLAIMER_FOOTER}"


def _to_ai_response(answer, *, trigger: AITrigger, stage: ChatStage, metadata: dict | None = None) -> AIResponse:
    text = answer.answer
    if stage == ChatStage.STAGE_3 and not text.startswith("For reference:"):
        text = _prefix_for_reference(text)
    response_metadata = {"stage": stage.value}
    if metadata:
        response_metadata.update(metadata)
    return AIResponse(
        text=text,
        citations=answer.citations,
        trigger=trigger,
        metadata=response_metadata,
    )


async def _build_dispute_response(case_id: str, question: str, stage: ChatStage) -> AIResponse:
    classification = await classify_dispute(question)
    if not classification.is_dispute:
        answer = await answer_policy_question(case_id, question)
        return _to_ai_response(answer, trigger=AITrigger.MENTION, stage=stage)

    answer = await answer_dispute_question(
        case_id,
        question,
        stage_instruction=build_stage_instruction(stage),
    )
    return _to_ai_response(
        answer,
        trigger=AITrigger.DISPUTE,
        stage=stage,
        metadata={
            "dispute_type": classification.dispute_type,
            "recommended_statute": classification.recommended_statute,
        },
    )


async def handle_chat_event(event: ChatEvent) -> AIResponse | None:
    stage = determine_stage(event.participants, event.invite_sent)

    if event.trigger == ChatEventTrigger.POLICY_INDEXED and stage == ChatStage.STAGE_1:
        answer = await summarize_policy_highlights(event.case_id, stage)
        return _to_ai_response(answer, trigger=AITrigger.PROACTIVE, stage=stage)

    if event.trigger == ChatEventTrigger.MESSAGE:
        if contains_ai_mention(event.message_text):
            question = extract_ai_question(event.message_text)
            if not question:
                return AIResponse(
                    text=f"Please add a question after @AI so I know what to look up.\n\n{DISCLAIMER_FOOTER}",
                    citations=[],
                    trigger=AITrigger.MENTION,
                    metadata={"stage": stage.value},
                )

            signal = detect_dispute_signal(question)
            if signal.triggered:
                return await _build_dispute_response(event.case_id, question, stage)

            answer = await answer_policy_question(event.case_id, question)
            return _to_ai_response(answer, trigger=AITrigger.MENTION, stage=stage)

        signal = detect_dispute_signal(event.message_text)
        if signal.triggered:
            return await _build_dispute_response(event.case_id, event.message_text, stage)

    return await maybe_get_deadline_alert(event.case_id, stage=stage)

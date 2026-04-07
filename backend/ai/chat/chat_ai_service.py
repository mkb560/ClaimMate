from __future__ import annotations

from ai.chat.mention_handler import contains_ai_mention, extract_ai_question
from ai.chat.stage_prompts import build_stage_instruction
from ai.chat.stage_router import determine_stage
from ai.deadline.deadline_checker import (
    explain_deadlines_for_case,
    is_deadline_question,
    maybe_get_deadline_alert,
)
from ai.dispute.keyword_filter import detect_dispute_signal
from ai.dispute.semantic_detector import classify_dispute
from ai.rag.prompt_templates import DISCLAIMER_FOOTER
from ai.rag.query_engine import answer_dispute_question, answer_policy_question, summarize_policy_highlights
from models.ai_types import AIResponse, AITrigger, AnswerResponse, ChatEvent, ChatEventTrigger, ChatStage


DISPUTE_NEXT_STEPS = {
    "DENIAL": {
        "happened": "this may be a claim denial dispute.",
        "collect": "the denial letter, claim number, policy pages, photos, estimates, and related messages.",
        "ask": "the written reason for the denial, the policy language used, and the next review step.",
    },
    "DELAY": {
        "happened": "this may be a claim delay or no-response issue.",
        "collect": "the claim timeline, notice date, proof-of-claim date, emails, call notes, and claim portal screenshots.",
        "ask": "the current claim status, what information is still missing, and when the next decision is expected.",
    },
    "AMOUNT": {
        "happened": "this may be a payment amount or underpayment dispute.",
        "collect": "repair estimates, invoices, photos, adjuster estimates, payment letters, and any supplement requests.",
        "ask": "how the amount was calculated, which line items were changed, and how to submit more evidence.",
    },
    "OTHER": {
        "happened": "this may be a claim-handling dispute.",
        "collect": "the claim number, timeline, policy pages, all written decisions, photos, estimates, and message history.",
        "ask": "for a written explanation, the claim-handling timeline, and the next escalation or review option.",
    },
}


def _prefix_for_reference(text: str) -> str:
    cleaned = text.replace(DISCLAIMER_FOOTER, "").strip()
    return f"For reference: {cleaned}\n\n{DISCLAIMER_FOOTER}"


def _strip_disclaimer(text: str) -> str:
    return text.replace(DISCLAIMER_FOOTER, "").strip()


def _append_dispute_next_steps(answer: AnswerResponse, *, dispute_type: str) -> AnswerResponse:
    steps = DISPUTE_NEXT_STEPS.get(dispute_type, DISPUTE_NEXT_STEPS["OTHER"])
    base_answer = _strip_disclaimer(answer.answer)
    helper = (
        "Next steps to consider:\n"
        f"- What happened: {steps['happened']}\n"
        f"- What to collect: {steps['collect']}\n"
        f"- What to ask the insurer: {steps['ask']}\n"
        "- Reminder: keep a written timeline and save copies of every response."
    )
    return AnswerResponse(
        answer=f"{base_answer}\n\n{helper}\n\n{DISCLAIMER_FOOTER}",
        citations=answer.citations,
        disclaimer=answer.disclaimer,
    )


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
    answer = _append_dispute_next_steps(answer, dispute_type=classification.dispute_type)
    return _to_ai_response(
        answer,
        trigger=AITrigger.DISPUTE,
        stage=stage,
        metadata={
            "dispute_type": classification.dispute_type,
            "recommended_statute": classification.recommended_statute,
            "next_step_helper": True,
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

            if is_deadline_question(question):
                return await explain_deadlines_for_case(event.case_id, stage=stage)

            signal = detect_dispute_signal(question)
            if signal.triggered:
                return await _build_dispute_response(event.case_id, question, stage)

            answer = await answer_policy_question(event.case_id, question)
            return _to_ai_response(answer, trigger=AITrigger.MENTION, stage=stage)

        signal = detect_dispute_signal(event.message_text)
        if signal.triggered:
            return await _build_dispute_response(event.case_id, event.message_text, stage)

    return await maybe_get_deadline_alert(event.case_id, stage=stage)

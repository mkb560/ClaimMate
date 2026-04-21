from __future__ import annotations

from ai.chat.mention_handler import contains_ai_mention, extract_ai_question
from ai.chat.stage_prompts import build_stage_instruction
from ai.chat.stage_router import determine_stage
from ai.deadline.deadline_checker import (
    explain_deadlines_for_case,
    is_deadline_question,
    maybe_get_deadline_alert,
)
from ai.dispute.keyword_filter import DisputeSignal, detect_dispute_signal
from ai.dispute.semantic_detector import STATUTE_BY_DISPUTE_TYPE, classify_dispute
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

INTERNAL_RESPONSE_METADATA_KEYS = {
    "case_chat_context",
    "case_report_payload",
}


def _prefix_for_reference(text: str) -> str:
    cleaned = text.replace(DISCLAIMER_FOOTER, "").strip()
    return f"For reference: {cleaned}\n\n{DISCLAIMER_FOOTER}"


def _strip_disclaimer(text: str) -> str:
    return text.replace(DISCLAIMER_FOOTER, "").strip()


def _public_response_metadata(metadata: dict | None) -> dict:
    if not metadata:
        return {}
    return {key: value for key, value in metadata.items() if key not in INTERNAL_RESPONSE_METADATA_KEYS}


def _dispute_helper_intro(stage: ChatStage) -> str:
    if stage == ChatStage.STAGE_1:
        return "A practical next-step plan:"
    if stage == ChatStage.STAGE_2:
        return "Before you involve the adjuster, here is a practical checklist:"
    return "A few practical next steps to keep the discussion organized:"


def _append_dispute_next_steps(
    answer: AnswerResponse,
    *,
    dispute_type: str,
    stage: ChatStage,
) -> AnswerResponse:
    steps = DISPUTE_NEXT_STEPS.get(dispute_type, DISPUTE_NEXT_STEPS["OTHER"])
    base_answer = _strip_disclaimer(answer.answer)
    helper = (
        f"{_dispute_helper_intro(stage)}\n"
        f"- What happened: {steps['happened']}\n"
        f"- Documents to gather: {steps['collect']}\n"
        f"- What to ask the insurer: {steps['ask']}\n"
        "- Reminder: keep a written timeline and save copies of every response."
    )
    return AnswerResponse(
        answer=f"{base_answer}\n\n{helper}\n\n{DISCLAIMER_FOOTER}",
        citations=answer.citations,
        disclaimer=answer.disclaimer,
    )


def _dispute_type_from_signal(signal: DisputeSignal) -> str:
    matched = {item.lower() for item in signal.matched}
    if matched & {"denied my claim", "claim denied", "refuse to pay", "rejection letter"}:
        return "DENIAL"
    if matched & {"underpaid", "wrong amount", "too low"}:
        return "AMOUNT"
    if matched & {"delay", "no response", "ignored"}:
        return "DELAY"
    return "OTHER"


def _to_ai_response(answer, *, trigger: AITrigger, stage: ChatStage, metadata: dict | None = None) -> AIResponse:
    text = answer.answer
    if stage == ChatStage.STAGE_3 and not text.startswith("For reference:"):
        text = _prefix_for_reference(text)
    response_metadata = {"stage": stage.value}
    response_metadata.update(_public_response_metadata(metadata))
    return AIResponse(
        text=text,
        citations=answer.citations,
        trigger=trigger,
        metadata=response_metadata,
    )


def _looks_like_case_context_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        marker in lowered
        for marker in (
            "accident",
            "incident",
            "what happened",
            "summary",
            "where",
            "location",
            "when",
            "time",
            "damage",
            "police",
            "injur",
            "photo",
            "missing",
            "follow up",
            "follow-up",
            "next step",
            "driver",
            "party",
            "vehicle",
            "report",
        )
    )


def _as_text_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _build_case_context_response(question: str, stage: ChatStage, metadata: dict | None) -> AIResponse | None:
    if not metadata or not _looks_like_case_context_question(question):
        return None

    chat_context = metadata.get("case_chat_context")
    report_payload = metadata.get("case_report_payload")
    if not isinstance(chat_context, dict) and not isinstance(report_payload, dict):
        return None

    lowered = question.lower()
    lines: list[str] = []
    response_kind = "summary"

    summary = ""
    if isinstance(chat_context, dict):
        summary = str(chat_context.get("summary") or "").strip()
    if not summary and isinstance(report_payload, dict):
        summary = str(report_payload.get("accident_summary") or "").strip()

    key_facts = _as_text_list(chat_context.get("key_facts") if isinstance(chat_context, dict) else [])
    follow_up_items = _as_text_list(chat_context.get("follow_up_items") if isinstance(chat_context, dict) else [])

    if any(marker in lowered for marker in ("missing", "follow up", "follow-up", "next step")):
        response_kind = "follow_up"
        if follow_up_items:
            lines.append("Based on the saved accident context, the current follow-up items are:")
            lines.append(_format_bullets(follow_up_items))
        else:
            lines.append("Based on the saved accident context, I do not see open follow-up items right now.")
    elif "damage" in lowered and isinstance(report_payload, dict):
        response_kind = "damage"
        damage = str(report_payload.get("damage_summary") or "").strip()
        narrative = str(report_payload.get("detailed_narrative") or "").strip()
        if damage:
            lines.append(f"Damage summary: {damage}")
        if narrative:
            lines.append(f"Relevant narrative: {narrative}")
    elif any(marker in lowered for marker in ("driver", "party", "vehicle")):
        response_kind = "parties"
        rows = report_payload.get("party_comparison_rows") if isinstance(report_payload, dict) else None
        if isinstance(rows, list) and rows:
            lines.append("The saved party comparison shows:")
            for row in rows:
                if not isinstance(row, dict):
                    continue
                label = row.get("field_label")
                owner = row.get("owner_value")
                other = row.get("other_party_value")
                lines.append(f"- {label}: owner = {owner}; other party = {other}")
    else:
        if summary:
            lines.append(f"Case summary: {summary}")
        if key_facts:
            lines.append("Key saved facts:")
            lines.append(_format_bullets(key_facts))

    if not lines:
        return None

    text = "\n".join(lines).strip() + f"\n\n{DISCLAIMER_FOOTER}"
    if stage == ChatStage.STAGE_3 and not text.startswith("For reference:"):
        text = _prefix_for_reference(text)
    return AIResponse(
        text=text,
        citations=[],
        trigger=AITrigger.MENTION,
        metadata={"stage": stage.value, "case_context_answer": True, "case_context_kind": response_kind},
    )


async def _build_question_response(case_id: str, question: str, stage: ChatStage, metadata: dict | None = None) -> AIResponse:
    if is_deadline_question(question):
        try:
            response = await explain_deadlines_for_case(case_id, stage=stage)
        except KeyError:
            return AIResponse(
                text=(
                    "I can't explain deadlines for this case because I could not find the saved case data. "
                    f"Reload or recreate the case, then try again.\n\n{DISCLAIMER_FOOTER}"
                ),
                citations=[],
                trigger=AITrigger.DEADLINE,
                metadata={"stage": stage.value, "deadline_intent": "explainer_missing_case"},
            )
        response.metadata.update(_public_response_metadata(metadata))
        return response

    signal = detect_dispute_signal(question)
    if signal.triggered:
        return await _build_dispute_response(
            case_id,
            question,
            stage,
            signal=signal,
            allow_policy_fallback=True,
        )

    if case_context_response := _build_case_context_response(question, stage, metadata):
        if metadata and metadata.get("direct_ai_chat") is True:
            case_context_response.metadata["direct_ai_chat"] = True
        return case_context_response

    answer = await answer_policy_question(case_id, question)
    return _to_ai_response(answer, trigger=AITrigger.MENTION, stage=stage, metadata=metadata)


async def _build_dispute_response(
    case_id: str,
    question: str,
    stage: ChatStage,
    *,
    signal: DisputeSignal | None = None,
    allow_policy_fallback: bool = True,
) -> AIResponse | None:
    classification = await classify_dispute(question)
    if not classification.is_dispute:
        if signal is not None and signal.confidence >= 0.9:
            inferred_dispute_type = _dispute_type_from_signal(signal)
            answer = await answer_dispute_question(
                case_id,
                question,
                stage_instruction=build_stage_instruction(stage),
            )
            answer = _append_dispute_next_steps(
                answer,
                dispute_type=inferred_dispute_type,
                stage=stage,
            )
            return _to_ai_response(
                answer,
                trigger=AITrigger.DISPUTE,
                stage=stage,
                metadata={
                    "dispute_type": inferred_dispute_type,
                    "recommended_statute": STATUTE_BY_DISPUTE_TYPE[inferred_dispute_type],
                    "next_step_helper": True,
                    "dispute_signal_only": True,
                },
            )
        if not allow_policy_fallback:
            return None
        answer = await answer_policy_question(case_id, question)
        return _to_ai_response(answer, trigger=AITrigger.MENTION, stage=stage)

    answer = await answer_dispute_question(
        case_id,
        question,
        stage_instruction=build_stage_instruction(stage),
    )
    answer = _append_dispute_next_steps(
        answer,
        dispute_type=classification.dispute_type,
        stage=stage,
    )
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

    if event.trigger in {ChatEventTrigger.PARTICIPANT_JOINED, ChatEventTrigger.POLICY_INDEXED}:
        return None

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

            return await _build_question_response(event.case_id, question, stage, event.metadata)

        if event.metadata.get("direct_ai_chat") is True:
            question = event.message_text.strip()
            if question:
                return await _build_question_response(
                    event.case_id,
                    question,
                    stage,
                    metadata=event.metadata,
                )

        signal = detect_dispute_signal(event.message_text)
        if signal.triggered:
            if response := await _build_dispute_response(
                event.case_id,
                event.message_text,
                stage,
                signal=signal,
                allow_policy_fallback=False,
            ):
                return response

    # Ambient deadline reminders are the final fallback when no proactive, mention,
    # or dispute response path produced an AI reply.
    return await maybe_get_deadline_alert(event.case_id, stage=stage)

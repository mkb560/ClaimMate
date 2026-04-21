from __future__ import annotations

from ai.clients import get_openai_client
from ai.chat.mention_handler import contains_ai_mention, extract_ai_question
from ai.chat.stage_prompts import build_stage_instruction
from ai.chat.stage_router import determine_stage
from ai.config import ai_config
from ai.deadline.deadline_checker import (
    explain_deadlines_for_case,
    is_deadline_question,
    maybe_get_deadline_alert,
)
from ai.dispute.keyword_filter import DisputeSignal, detect_dispute_signal
from ai.dispute.semantic_detector import STATUTE_BY_DISPUTE_TYPE, classify_dispute
from ai.rag.prompt_templates import DISCLAIMER_FOOTER
from ai.rag.prompt_templates import NOT_ENOUGH_INFO_MESSAGE
from ai.rag.query_engine import answer_dispute_question, answer_policy_question, summarize_policy_highlights
from ai.rag.regulatory_fact_extractor import is_structured_regulatory_question
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

POLICY_OR_COVERAGE_MARKERS = (
    "policy",
    "coverage",
    "cover",
    "covered",
    "deductible",
    "limit",
    "limits",
    "liability",
    "collision",
    "comprehensive",
    "rental",
    "claim rule",
    "exclusion",
)

OPEN_CHAT_SYSTEM_PROMPT = """You are ClaimMate, a friendly AI copilot for car insurance claims.

You should feel conversational and helpful, not like a rigid keyword router.

Rules:
1. If the user asks a normal general-knowledge question, answer it briefly and directly.
2. If the user asks about the saved accident/case, use the saved case context when it is relevant.
3. If the user asks about policy language, coverage, legal rights, deadlines, or disputes, be careful and avoid making coverage guarantees.
4. Do not invent case facts or policy facts that are not in the provided context.
5. Keep the answer concise, usually 1 to 4 short sentences.
6. If the question is unrelated to insurance, answer it, then gently offer to help with the claim if useful.
7. If the user asks for a draft, checklist, template, summary, or translation, complete the task directly using the saved context when relevant.
8. If the user asks in another language, answer in that language.
9. If the user asks for legal advice, exact compensation, or a guaranteed outcome, say you cannot provide that certainty and give safe practical next steps.
"""


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
    if NOT_ENOUGH_INFO_MESSAGE.lower() in base_answer.lower():
        base_answer = (
            "I don't have enough specific claim-handling details yet to assess the dispute confidently, "
            "but you can still use this next-step checklist to organize the conversation."
        )
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
    if matched & {
        "underpaid",
        "wrong amount",
        "too low",
        "disagree with the repair amount",
        "disagree with the estimate",
        "dispute the repair amount",
        "repair estimate is too low",
        "settlement amount is too low",
        "repair amount",
        "settlement amount",
    }:
        return "AMOUNT"
    if matched & {
        "delay",
        "delayed",
        "no response",
        "ignored",
        "has not responded",
        "have not responded",
        "haven't responded",
        "not responded",
        "not responding",
    }:
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


def _looks_like_policy_or_coverage_question(question: str) -> bool:
    lowered = question.lower()
    return any(marker in lowered for marker in POLICY_OR_COVERAGE_MARKERS)


def _should_try_grounded_answer(question: str) -> bool:
    return _looks_like_policy_or_coverage_question(question) or is_structured_regulatory_question(question)


def _rag_case_context_from_metadata(metadata: dict | None) -> dict | None:
    if not metadata:
        return None
    chat_context = metadata.get("case_chat_context")
    report_payload = metadata.get("case_report_payload")
    if not isinstance(chat_context, dict) and not isinstance(report_payload, dict):
        return None
    return {
        "chat_context": chat_context if isinstance(chat_context, dict) else None,
        "report_payload": report_payload if isinstance(report_payload, dict) else None,
    }


async def _answer_policy_with_context(
    case_id: str,
    question: str,
    *,
    case_context: dict | None = None,
):
    if case_context:
        return await answer_policy_question(case_id, question, case_context=case_context)
    return await answer_policy_question(case_id, question)


async def _answer_dispute_with_context(
    case_id: str,
    question: str,
    *,
    stage_instruction: str | None,
    case_context: dict | None = None,
):
    if case_context:
        return await answer_dispute_question(
            case_id,
            question,
            stage_instruction=stage_instruction,
            case_context=case_context,
        )
    return await answer_dispute_question(
        case_id,
        question,
        stage_instruction=stage_instruction,
    )


def _is_not_enough_answer(answer: AnswerResponse) -> bool:
    return NOT_ENOUGH_INFO_MESSAGE.lower() in answer.answer.lower()


def _as_text_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _format_bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _value_from_report(metadata: dict | None, key: str) -> str | None:
    if not isinstance(metadata, dict):
        return None
    report_payload = metadata.get("case_report_payload")
    if not isinstance(report_payload, dict):
        return None
    value = str(report_payload.get(key) or "").strip()
    return value or None


def _build_open_chat_context(metadata: dict | None) -> str:
    if not metadata:
        return "No saved case context is available."
    chat_context = metadata.get("case_chat_context")
    report_payload = metadata.get("case_report_payload")
    lines: list[str] = []

    if isinstance(chat_context, dict):
        if summary := str(chat_context.get("summary") or "").strip():
            lines.append(f"Case summary: {summary}")
        key_facts = _as_text_list(chat_context.get("key_facts"))
        if key_facts:
            lines.append("Key saved facts:")
            lines.append(_format_bullets(key_facts))
        follow_up_items = _as_text_list(chat_context.get("follow_up_items"))
        if follow_up_items:
            lines.append("Open follow-up items:")
            lines.append(_format_bullets(follow_up_items))

    if isinstance(report_payload, dict):
        for label, key in (
            ("Accident summary", "accident_summary"),
            ("Location", "location_summary"),
            ("Damage summary", "damage_summary"),
            ("Detailed narrative", "detailed_narrative"),
            ("Police report number", "police_report_number"),
            ("Repair shop", "repair_shop_name"),
            ("Adjuster", "adjuster_name"),
        ):
            if value := str(report_payload.get(key) or "").strip():
                lines.append(f"{label}: {value}")

    return "\n".join(lines)[:5000] if lines else "No saved case context is available."


def _build_open_chat_fallback(question: str, metadata: dict | None = None) -> str:
    lowered = question.lower()
    location = _value_from_report(metadata, "location_summary") or "the saved accident location"
    damage = _value_from_report(metadata, "damage_summary") or "the saved vehicle damage"
    police_report = _value_from_report(metadata, "police_report_number")
    repair_shop = _value_from_report(metadata, "repair_shop_name") or "the repair shop"
    adjuster = _value_from_report(metadata, "adjuster_name") or "the adjuster"

    if "checklist" in lowered and ("repair" in lowered or "estimate" in lowered):
        return (
            "Here is a repair-estimate conversation checklist:\n"
            f"- Confirm the estimate covers the visible damage: {damage}.\n"
            "- Ask whether hidden damage, diagnostics, and sensor or ADAS recalibration are included.\n"
            f"- Bring or upload photos, the police report number{f' ({police_report})' if police_report else ''}, "
            "insurance-exchange details, and any shop notes.\n"
            f"- Ask {adjuster} how supplements work if {repair_shop} finds more damage after teardown.\n"
            "- Ask for a line-item explanation of any denied, reduced, or delayed repair items."
        )

    if _contains_cjk(question):
        return (
            f"这个事故可以这样总结：你的车辆在 {location} 附近发生追尾事故；记录显示车辆有损伤，"
            f"主要包括 {damage}。"
            f"{f' 警方记录号是 {police_report}。' if police_report else ''}"
            "建议继续保留照片、维修估价、保险沟通记录，并让理赔员用书面方式说明下一步。"
        )

    if "legal advice" in lowered or "compensation" in lowered or "guarantee" in lowered:
        return (
            "I can't provide legal advice, exact compensation amounts, or a guaranteed claim outcome. "
            "A safer next step is to organize the repair estimate, photos, police report, policy pages, "
            "and written insurer responses, then ask the adjuster for a written coverage and payment explanation."
        )

    return "I’m not sure how to answer that yet, but I can still help with the claim details."


async def _answer_open_chat_question(
    question: str,
    stage: ChatStage,
    metadata: dict | None = None,
) -> AIResponse:
    client = get_openai_client()
    response = await client.chat.completions.create(
        model=ai_config.rag_model,
        reasoning_effort=ai_config.rag_reasoning_effort,
        messages=[
            {"role": "system", "content": OPEN_CHAT_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"<saved_case_context>\n{_build_open_chat_context(metadata)}\n</saved_case_context>\n\n"
                    f"Question: {question}"
                ),
            },
        ],
        max_completion_tokens=700,
    )
    raw_text = (response.choices[0].message.content or "").strip()
    text = raw_text or _build_open_chat_fallback(question, metadata)
    if DISCLAIMER_FOOTER not in text:
        text = f"{text}\n\n{DISCLAIMER_FOOTER}"
    if stage == ChatStage.STAGE_3 and not text.startswith("For reference:"):
        text = _prefix_for_reference(text)
    response_metadata = {"stage": stage.value, "open_chat_answer": True}
    response_metadata.update(_public_response_metadata(metadata))
    return AIResponse(
        text=text,
        citations=[],
        trigger=AITrigger.MENTION,
        metadata=response_metadata,
    )


async def _build_question_response(case_id: str, question: str, stage: ChatStage, metadata: dict | None = None) -> AIResponse:
    case_context = _rag_case_context_from_metadata(metadata)
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
            case_context=case_context,
        )

    if case_context and not _should_try_grounded_answer(question):
        return await _answer_open_chat_question(question, stage, metadata)

    answer = await _answer_policy_with_context(case_id, question, case_context=case_context)
    if _is_not_enough_answer(answer):
        return await _answer_open_chat_question(question, stage, metadata)
    return _to_ai_response(answer, trigger=AITrigger.MENTION, stage=stage, metadata=metadata)


async def _build_dispute_response(
    case_id: str,
    question: str,
    stage: ChatStage,
    *,
    signal: DisputeSignal | None = None,
    allow_policy_fallback: bool = True,
    case_context: dict | None = None,
) -> AIResponse | None:
    classification = await classify_dispute(question)
    if not classification.is_dispute:
        if signal is not None and signal.confidence >= 0.9:
            inferred_dispute_type = _dispute_type_from_signal(signal)
            answer = await _answer_dispute_with_context(
                case_id,
                question,
                stage_instruction=build_stage_instruction(stage),
                case_context=case_context,
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
        answer = await _answer_policy_with_context(case_id, question, case_context=case_context)
        return _to_ai_response(answer, trigger=AITrigger.MENTION, stage=stage)

    answer = await _answer_dispute_with_context(
        case_id,
        question,
        stage_instruction=build_stage_instruction(stage),
        case_context=case_context,
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
                case_context=_rag_case_context_from_metadata(event.metadata),
            ):
                return response

    # Ambient deadline reminders are the final fallback when no proactive, mention,
    # or dispute response path produced an AI reply.
    return await maybe_get_deadline_alert(event.case_id, stage=stage)

from __future__ import annotations

import argparse
import asyncio
import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from ai.chat import chat_ai_service
from ai.dispute.semantic_detector import DisputeClassification
from ai.rag.prompt_templates import DISCLAIMER_FOOTER
from models.ai_types import (
    AIResponse,
    AITrigger,
    AnswerResponse,
    ChatEvent,
    ChatEventTrigger,
    ChatStage,
    Citation,
    Participant,
)


@dataclass(frozen=True, slots=True)
class ChatEvalCase:
    name: str
    event: ChatEvent
    expected_trigger: AITrigger
    expected_stage: ChatStage
    expected_text_contains: tuple[str, ...] = ()
    expected_text_prefix: str | None = None
    expected_metadata: dict[str, Any] = field(default_factory=dict)
    require_citations: bool = False


@dataclass(slots=True)
class ChatEvalResult:
    name: str
    ok: bool
    detail: str
    response: dict[str, Any] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run deterministic chat AI orchestration checks without calling OpenAI or a live database."
        )
    )
    parser.add_argument("--json-out", help="Optional path to write JSON results.")
    return parser.parse_args()


def _owner_participants() -> list[Participant]:
    return [Participant(user_id="owner-1", role="owner")]


def _stage_3_participants() -> list[Participant]:
    return [
        Participant(user_id="owner-1", role="owner"),
        Participant(user_id="adjuster-1", role="adjuster"),
    ]


def _citation(source_type: str = "kb_a") -> Citation:
    return Citation(
        source_type=source_type,
        source_label="Demo source",
        document_id="demo-doc",
        page_num=1,
        excerpt="Demo citation excerpt.",
    )


def _answer(text: str, *, source_type: str = "kb_a") -> AnswerResponse:
    return AnswerResponse(
        answer=f"{text} [S1]\n\n{DISCLAIMER_FOOTER}",
        citations=[_citation(source_type)],
        disclaimer=DISCLAIMER_FOOTER,
    )


async def _fake_answer_policy_question(case_id: str, question: str) -> AnswerResponse:
    lowered = question.lower()
    if "15-day" in lowered or "acknowledgment" in lowered:
        return _answer(
            "California insurers generally must acknowledge notice of a claim within 15 calendar days.",
            source_type="kb_b",
        )
    return _answer("Your policy includes rental reimbursement support for eligible covered losses.")


async def _fake_answer_dispute_question(
    case_id: str,
    question: str,
    *,
    stage_instruction: str,
) -> AnswerResponse:
    return _answer(
        "The denial may implicate California fair claims handling rules, so the user should review the denial reason and saved claim documents.",
        source_type="kb_b",
    )


async def _fake_summarize_policy_highlights(case_id: str, stage: ChatStage) -> AnswerResponse:
    return _answer("Your policy has been indexed and is ready for questions.")


async def _fake_maybe_get_deadline_alert(case_id: str, *, stage: ChatStage) -> AIResponse | None:
    if case_id != "deadline-case":
        return None
    opener = "For reference: " if stage == ChatStage.STAGE_3 else ""
    return AIResponse(
        text=(
            f"{opener}Deadline reminder: based on the saved claim notice date, "
            f"the California acknowledgment timeline is due soon.\n\n{DISCLAIMER_FOOTER}"
        ),
        citations=[],
        trigger=AITrigger.DEADLINE,
        metadata={"stage": stage.value, "deadline_type": "acknowledgment"},
    )


async def _fake_explain_deadlines_for_case(case_id: str, *, stage: ChatStage) -> AIResponse:
    opener = "For reference: " if stage == ChatStage.STAGE_3 else ""
    return AIResponse(
        text=(
            f"{opener}Deadline overview based on saved case dates:\n"
            "- acknowledgment: due on 2026-04-16 from the claim notice date; currently due in 2 day(s).\n"
            "- decision: due on 2026-05-15 from the proof-of-claim date; currently due in 31 day(s).\n"
            "Common rule of thumb: track the 15-day acknowledgment window after notice of claim and the 40-day decision window after proof of claim."
            f"\n\n{DISCLAIMER_FOOTER}"
        ),
        citations=[],
        trigger=AITrigger.DEADLINE,
        metadata={
            "stage": stage.value,
            "deadline_intent": "explainer",
            "tracked_windows": [
                {"deadline_type": "acknowledgment", "due_at": "2026-04-16T00:00:00+00:00"},
                {"deadline_type": "decision", "due_at": "2026-05-15T00:00:00+00:00"},
            ],
        },
    )


async def _fake_classify_dispute(message_text: str) -> DisputeClassification:
    lowered = message_text.lower()
    if "rejection letter" in lowered:
        return DisputeClassification(
            is_dispute=False,
            dispute_type="NOT_DISPUTE",
            recommended_statute=None,
            rationale="Demo classifier fallback.",
        )
    if "denied" in lowered or "claim denied" in lowered:
        return DisputeClassification(
            is_dispute=True,
            dispute_type="DENIAL",
            recommended_statute="10 CCR 2695.7(b)",
            rationale="Demo denial signal.",
        )
    return DisputeClassification(
        is_dispute=False,
        dispute_type="NOT_DISPUTE",
        recommended_statute=None,
        rationale="No demo dispute signal.",
    )


@contextmanager
def _patched_chat_dependencies():
    replacements: dict[str, Callable[..., Any]] = {
        "answer_policy_question": _fake_answer_policy_question,
        "answer_dispute_question": _fake_answer_dispute_question,
        "summarize_policy_highlights": _fake_summarize_policy_highlights,
        "maybe_get_deadline_alert": _fake_maybe_get_deadline_alert,
        "explain_deadlines_for_case": _fake_explain_deadlines_for_case,
        "classify_dispute": _fake_classify_dispute,
    }
    originals = {name: getattr(chat_ai_service, name) for name in replacements}
    try:
        for name, replacement in replacements.items():
            setattr(chat_ai_service, name, replacement)
        yield
    finally:
        for name, original in originals.items():
            setattr(chat_ai_service, name, original)


def _build_eval_cases() -> list[ChatEvalCase]:
    return [
        ChatEvalCase(
            name="empty_mention_requires_question",
            event=ChatEvent(
                case_id="case-1",
                sender_role="owner",
                message_text="@AI",
                participants=_owner_participants(),
                invite_sent=False,
                trigger=ChatEventTrigger.MESSAGE,
            ),
            expected_trigger=AITrigger.MENTION,
            expected_stage=ChatStage.STAGE_1,
            expected_text_contains=("Please add a question after @AI",),
        ),
        ChatEvalCase(
            name="stage_1_regulatory_mention",
            event=ChatEvent(
                case_id="case-1",
                sender_role="owner",
                message_text="@AI What is the 15-day claim acknowledgment rule?",
                participants=_owner_participants(),
                invite_sent=False,
                trigger=ChatEventTrigger.MESSAGE,
            ),
            expected_trigger=AITrigger.MENTION,
            expected_stage=ChatStage.STAGE_1,
            expected_text_contains=("15 calendar days",),
            require_citations=True,
        ),
        ChatEvalCase(
            name="stage_3_neutral_policy_mention",
            event=ChatEvent(
                case_id="case-1",
                sender_role="owner",
                message_text="@AI does this policy cover rental reimbursement?",
                participants=_stage_3_participants(),
                invite_sent=True,
                trigger=ChatEventTrigger.MESSAGE,
            ),
            expected_trigger=AITrigger.MENTION,
            expected_stage=ChatStage.STAGE_3,
            expected_text_prefix="For reference:",
            expected_text_contains=("rental reimbursement",),
            require_citations=True,
        ),
        ChatEvalCase(
            name="stage_3_non_mention_dispute",
            event=ChatEvent(
                case_id="case-1",
                sender_role="owner",
                message_text="The insurer denied my claim and I need help understanding the denial.",
                participants=_stage_3_participants(),
                invite_sent=True,
                trigger=ChatEventTrigger.MESSAGE,
            ),
            expected_trigger=AITrigger.DISPUTE,
            expected_stage=ChatStage.STAGE_3,
            expected_text_prefix="For reference:",
            expected_text_contains=("denial", "Next steps to consider", "What to collect"),
            expected_metadata={
                "dispute_type": "DENIAL",
                "recommended_statute": "10 CCR 2695.7(b)",
                "next_step_helper": True,
            },
            require_citations=True,
        ),
        ChatEvalCase(
            name="stage_3_keyword_only_dispute_fallback",
            event=ChatEvent(
                case_id="case-1",
                sender_role="owner",
                message_text="I received a rejection letter and need help understanding what happened.",
                participants=_stage_3_participants(),
                invite_sent=True,
                trigger=ChatEventTrigger.MESSAGE,
            ),
            expected_trigger=AITrigger.DISPUTE,
            expected_stage=ChatStage.STAGE_3,
            expected_text_prefix="For reference:",
            expected_text_contains=("Next steps to consider", "What to collect", "written reason"),
            expected_metadata={
                "dispute_type": "DENIAL",
                "recommended_statute": "10 CCR §2695.7(b)",
                "next_step_helper": True,
                "dispute_signal_only": True,
            },
            require_citations=True,
        ),
        ChatEvalCase(
            name="stage_1_deadline_explainer_mention",
            event=ChatEvent(
                case_id="deadline-case",
                sender_role="owner",
                message_text="@AI what deadlines should I know for this claim?",
                participants=_owner_participants(),
                invite_sent=False,
                trigger=ChatEventTrigger.MESSAGE,
            ),
            expected_trigger=AITrigger.DEADLINE,
            expected_stage=ChatStage.STAGE_1,
            expected_text_contains=("Deadline overview", "15-day acknowledgment", "40-day decision"),
            expected_metadata={"deadline_intent": "explainer"},
        ),
        ChatEvalCase(
            name="stage_1_deadline_fallback",
            event=ChatEvent(
                case_id="deadline-case",
                sender_role="owner",
                message_text="Just checking in on my claim.",
                participants=_owner_participants(),
                invite_sent=False,
                trigger=ChatEventTrigger.MESSAGE,
            ),
            expected_trigger=AITrigger.DEADLINE,
            expected_stage=ChatStage.STAGE_1,
            expected_text_contains=("Deadline reminder",),
            expected_metadata={"deadline_type": "acknowledgment"},
        ),
        ChatEvalCase(
            name="stage_1_policy_indexed_proactive",
            event=ChatEvent(
                case_id="case-1",
                sender_role="system",
                message_text="",
                participants=_owner_participants(),
                invite_sent=False,
                trigger=ChatEventTrigger.POLICY_INDEXED,
            ),
            expected_trigger=AITrigger.PROACTIVE,
            expected_stage=ChatStage.STAGE_1,
            expected_text_contains=("indexed",),
            require_citations=True,
        ),
    ]


def _serialize_response(response: AIResponse | None) -> dict[str, Any] | None:
    if response is None:
        return None
    return asdict(response)


def _validate_response(eval_case: ChatEvalCase, response: AIResponse | None) -> None:
    if response is None:
        raise ValueError("Expected an AI response but got None.")
    if response.trigger != eval_case.expected_trigger:
        raise ValueError(f"Expected trigger {eval_case.expected_trigger}, got {response.trigger}.")
    if response.metadata.get("stage") != eval_case.expected_stage.value:
        raise ValueError(
            f"Expected stage metadata {eval_case.expected_stage.value!r}, got {response.metadata.get('stage')!r}."
        )
    if eval_case.expected_text_prefix and not response.text.startswith(eval_case.expected_text_prefix):
        raise ValueError(f"Expected text to start with {eval_case.expected_text_prefix!r}.")
    for expected_text in eval_case.expected_text_contains:
        if expected_text.lower() not in response.text.lower():
            raise ValueError(f"Expected text to contain {expected_text!r}.")
    for key, expected_value in eval_case.expected_metadata.items():
        if response.metadata.get(key) != expected_value:
            raise ValueError(f"Expected metadata[{key!r}] = {expected_value!r}.")
    if eval_case.require_citations and not response.citations:
        raise ValueError("Expected at least one citation.")


async def run_eval() -> list[ChatEvalResult]:
    results: list[ChatEvalResult] = []
    with _patched_chat_dependencies():
        for eval_case in _build_eval_cases():
            try:
                response = await chat_ai_service.handle_chat_event(eval_case.event)
                _validate_response(eval_case, response)
            except Exception as exc:
                results.append(
                    ChatEvalResult(
                        name=eval_case.name,
                        ok=False,
                        detail=str(exc),
                    )
                )
                continue
            results.append(
                ChatEvalResult(
                    name=eval_case.name,
                    ok=True,
                    detail="ok",
                    response=_serialize_response(response),
                )
            )
    return results


def _write_json(path: str, payload: Any) -> None:
    output_path = Path(path).expanduser().resolve()
    output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


async def async_main() -> int:
    args = parse_args()
    results = await run_eval()
    passed = sum(item.ok for item in results)

    print(f"Chat AI eval summary: {passed}/{len(results)} passed")
    for item in results:
        status = "PASS" if item.ok else "FAIL"
        print(f"[{status}] {item.name}: {item.detail}")

    if args.json_out:
        _write_json(args.json_out, {"results": [asdict(item) for item in results]})
        print(f"Saved JSON results to {Path(args.json_out).expanduser().resolve()}")

    return 0 if passed == len(results) else 1


def main() -> None:
    raise SystemExit(asyncio.run(async_main()))


if __name__ == "__main__":
    main()

from unittest.mock import AsyncMock

from ai.dispute.semantic_detector import DisputeClassification
from ai.rag.prompt_templates import DISCLAIMER_FOOTER
from models.ai_types import AIResponse, AITrigger, AnswerResponse, ChatEvent, ChatEventTrigger, ChatStage, Participant


async def test_handle_chat_event_requires_question_after_mention() -> None:
    from ai.chat.chat_ai_service import handle_chat_event

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="@AI",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.MENTION
    assert "Please add a question after @AI" in response.text


async def test_handle_chat_event_prefixes_stage_3_answer(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    async def fake_answer_policy_question(case_id: str, question: str):
        return AnswerResponse(
            answer="Your rental reimbursement is $30/day. [S1]\n\nDisclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
            citations=[],
            disclaimer="Disclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
        )

    async def fake_deadline_alert(case_id: str, *, stage: ChatStage):
        return None

    monkeypatch.setattr(chat_ai_service, "answer_policy_question", fake_answer_policy_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", fake_deadline_alert)

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="@AI does this policy cover rental reimbursement?",
        participants=[
            Participant(user_id="1", role="owner"),
            Participant(user_id="2", role="adjuster"),
        ],
        invite_sent=True,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.text.startswith("For reference:")
    assert response.trigger == AITrigger.MENTION


async def test_handle_chat_event_policy_indexed_stage_1(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    async def fake_summary(case_id: str, stage: ChatStage):
        return AnswerResponse(
            answer="Your policy is indexed.\n\nDisclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
            citations=[],
            disclaimer="Disclaimer: This is general information only and does not constitute legal or insurance advice. Consult a licensed professional for your specific situation.",
        )

    monkeypatch.setattr(chat_ai_service, "summarize_policy_highlights", fake_summary)

    event = ChatEvent(
        case_id="case-1",
        sender_role="system",
        message_text="",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.POLICY_INDEXED,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.PROACTIVE


async def test_handle_chat_event_mention_takes_precedence_over_deadline(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    deadline_called = False

    async def fake_answer_policy_question(case_id: str, question: str):
        return AnswerResponse(
            answer=f"Your policy includes rental reimbursement. [S1]\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    async def fake_deadline_alert(case_id: str, *, stage: ChatStage):
        nonlocal deadline_called
        deadline_called = True
        return AIResponse(
            text=f"Deadline reminder.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            trigger=AITrigger.DEADLINE,
            metadata={"stage": stage.value},
        )

    monkeypatch.setattr(chat_ai_service, "answer_policy_question", fake_answer_policy_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", fake_deadline_alert)

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="@AI does this policy cover rental reimbursement?",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.MENTION
    assert "rental reimbursement" in response.text
    assert deadline_called is False


async def test_handle_chat_event_direct_ai_chat_answers_without_mention(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    async def fake_answer_policy_question(case_id: str, question: str):
        assert question == "Does my policy include rental reimbursement?"
        return AnswerResponse(
            answer=f"Your policy includes rental reimbursement. [S1]\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    monkeypatch.setattr(chat_ai_service, "answer_policy_question", fake_answer_policy_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", AsyncMock(return_value=None))

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="Does my policy include rental reimbursement?",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
        metadata={"direct_ai_chat": True},
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.MENTION
    assert response.metadata["stage"] == ChatStage.STAGE_1.value
    assert response.metadata["direct_ai_chat"] is True
    assert "rental reimbursement" in response.text


async def test_handle_chat_event_uses_saved_case_context_for_accident_questions(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    policy_called = False

    async def fake_answer_policy_question(case_id: str, question: str):
        nonlocal policy_called
        policy_called = True
        return AnswerResponse(
            answer=f"Policy answer.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    monkeypatch.setattr(chat_ai_service, "answer_policy_question", fake_answer_policy_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", AsyncMock(return_value=None))

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="What happened in the accident?",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
        metadata={
            "direct_ai_chat": True,
            "case_chat_context": {
                "summary": "Rear-end collision at a red light. Both drivers exchanged insurance information.",
                "key_facts": ["Police called: Yes", "Injuries reported: No"],
                "follow_up_items": [],
            },
        },
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.MENTION
    assert response.metadata["case_context_answer"] is True
    assert response.metadata["direct_ai_chat"] is True
    assert "case_chat_context" not in response.metadata
    assert "Rear-end collision" in response.text
    assert policy_called is False


async def test_handle_chat_event_passes_saved_case_context_to_policy_rag_for_coverage_questions(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    captured: dict[str, object] = {}

    async def fake_answer_policy_question(case_id: str, question: str, **kwargs):
        captured["case_id"] = case_id
        captured["question"] = question
        captured["case_context"] = kwargs.get("case_context")
        return AnswerResponse(
            answer=f"Based on the accident context, check collision coverage. [S1]\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    monkeypatch.setattr(chat_ai_service, "answer_policy_question", fake_answer_policy_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", AsyncMock(return_value=None))

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="Based on my accident, what policy coverage should I check?",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
        metadata={
            "direct_ai_chat": True,
            "case_chat_context": {
                "summary": "Rear-end collision at a red light.",
                "key_facts": ["Police called: Yes"],
            },
            "case_report_payload": {"damage_summary": "Rear bumper damage."},
        },
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.MENTION
    assert response.metadata["direct_ai_chat"] is True
    assert response.metadata.get("case_context_answer") is None
    assert captured["case_id"] == "case-1"
    assert captured["question"] == "Based on my accident, what policy coverage should I check?"
    assert captured["case_context"] == {
        "chat_context": {
            "summary": "Rear-end collision at a red light.",
            "key_facts": ["Police called: Yes"],
        },
        "report_payload": {"damage_summary": "Rear bumper damage."},
    }


async def test_handle_chat_event_non_mention_dispute_takes_precedence_over_deadline(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    deadline_called = False

    async def fake_classify_dispute(message_text: str):
        return DisputeClassification(
            is_dispute=True,
            dispute_type="DENIAL",
            recommended_statute="10 CCR 2695.7(b)",
            rationale="Demo denial signal.",
        )

    async def fake_answer_dispute_question(case_id: str, question: str, *, stage_instruction: str):
        return AnswerResponse(
            answer=f"The denial may require reviewing the insurer's stated reason. [S1]\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    async def fake_deadline_alert(case_id: str, *, stage: ChatStage):
        nonlocal deadline_called
        deadline_called = True
        return AIResponse(
            text=f"Deadline reminder.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            trigger=AITrigger.DEADLINE,
            metadata={"stage": stage.value},
        )

    monkeypatch.setattr(chat_ai_service, "classify_dispute", fake_classify_dispute)
    monkeypatch.setattr(chat_ai_service, "answer_dispute_question", fake_answer_dispute_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", fake_deadline_alert)

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="The insurer denied my claim and I need help understanding the denial.",
        participants=[
            Participant(user_id="1", role="owner"),
            Participant(user_id="2", role="adjuster"),
        ],
        invite_sent=True,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.DISPUTE
    assert response.text.startswith("For reference:")
    assert response.metadata["stage"] == ChatStage.STAGE_3.value
    assert response.metadata["dispute_type"] == "DENIAL"
    assert response.metadata["recommended_statute"] == "10 CCR 2695.7(b)"
    assert response.metadata["next_step_helper"] is True
    assert "A few practical next steps to keep the discussion organized:" in response.text
    assert "Documents to gather:" in response.text
    assert "denial letter" in response.text
    assert deadline_called is False


async def test_handle_chat_event_hard_dispute_signal_stays_on_dispute_path_when_classifier_is_inconclusive(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    policy_called = False

    async def fake_classify_dispute(message_text: str):
        return DisputeClassification(
            is_dispute=False,
            dispute_type="NOT_DISPUTE",
            recommended_statute=None,
            rationale="Classifier inconclusive.",
        )

    async def fake_answer_policy_question(case_id: str, question: str):
        nonlocal policy_called
        policy_called = True
        return AnswerResponse(
            answer=f"Generic policy answer.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    async def fake_answer_dispute_question(case_id: str, question: str, *, stage_instruction: str):
        return AnswerResponse(
            answer=(
                "I don't have enough information in the uploaded policy and regulatory materials to answer that confidently."
                f"\n\n{DISCLAIMER_FOOTER}"
            ),
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    monkeypatch.setattr(chat_ai_service, "classify_dispute", fake_classify_dispute)
    monkeypatch.setattr(chat_ai_service, "answer_policy_question", fake_answer_policy_question)
    monkeypatch.setattr(chat_ai_service, "answer_dispute_question", fake_answer_dispute_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", AsyncMock(return_value=None))

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="The insurer denied my claim and I need help understanding the denial.",
        participants=[
            Participant(user_id="1", role="owner"),
            Participant(user_id="2", role="adjuster"),
        ],
        invite_sent=True,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.DISPUTE
    assert response.text.startswith("For reference:")
    assert "don't have enough information" in response.text
    assert "A few practical next steps to keep the discussion organized:" in response.text
    assert response.metadata["dispute_type"] == "DENIAL"
    assert response.metadata["recommended_statute"] == "10 CCR §2695.7(b)"
    assert response.metadata["dispute_signal_only"] is True
    assert policy_called is False


async def test_handle_chat_event_stage_2_delay_dispute_uses_stage_2_checklist_wording(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    async def fake_classify_dispute(message_text: str):
        return DisputeClassification(
            is_dispute=True,
            dispute_type="DELAY",
            recommended_statute="10 CCR §2695.5(e) / §2695.7(c)",
            rationale="Demo delay signal.",
        )

    async def fake_answer_dispute_question(case_id: str, question: str, *, stage_instruction: str):
        assert "preparing to involve an adjuster" in stage_instruction
        return AnswerResponse(
            answer=(
                f"The delay may implicate California claim-handling timelines, so the owner should organize the claim timeline "
                f"and supporting documents before the next adjuster conversation. [S1]\n\n{DISCLAIMER_FOOTER}"
            ),
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    monkeypatch.setattr(chat_ai_service, "classify_dispute", fake_classify_dispute)
    monkeypatch.setattr(chat_ai_service, "answer_dispute_question", fake_answer_dispute_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", AsyncMock(return_value=None))

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="The insurer still has no response and the claim is delayed.",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=True,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.DISPUTE
    assert response.metadata["stage"] == ChatStage.STAGE_2.value
    assert response.metadata["dispute_type"] == "DELAY"
    assert "Before you involve the adjuster, here is a practical checklist:" in response.text
    assert "Documents to gather:" in response.text
    assert "claim timeline" in response.text
    assert not response.text.startswith("For reference:")


async def test_handle_chat_event_stage_3_amount_dispute_uses_amount_specific_wording(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    async def fake_classify_dispute(message_text: str):
        return DisputeClassification(
            is_dispute=True,
            dispute_type="AMOUNT",
            recommended_statute="10 CCR §2695.8",
            rationale="Demo amount signal.",
        )

    async def fake_answer_dispute_question(case_id: str, question: str, *, stage_instruction: str):
        return AnswerResponse(
            answer=(
                f"The amount dispute may require comparing repair estimates and asking the insurer for a written explanation "
                f"of how the payment was calculated. [S1]\n\n{DISCLAIMER_FOOTER}"
            ),
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    monkeypatch.setattr(chat_ai_service, "classify_dispute", fake_classify_dispute)
    monkeypatch.setattr(chat_ai_service, "answer_dispute_question", fake_answer_dispute_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", AsyncMock(return_value=None))

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="The repair estimate is too low and I think the insurer underpaid me.",
        participants=[
            Participant(user_id="1", role="owner"),
            Participant(user_id="2", role="adjuster"),
        ],
        invite_sent=True,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.DISPUTE
    assert response.text.startswith("For reference:")
    assert response.metadata["dispute_type"] == "AMOUNT"
    assert response.metadata["recommended_statute"] == "10 CCR §2695.8"
    assert "repair estimates" in response.text
    assert "payment was calculated" in response.text


async def test_handle_chat_event_explicit_deadline_mention_uses_deadline_explainer(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    policy_called = False
    dispute_called = False

    async def fake_answer_policy_question(case_id: str, question: str):
        nonlocal policy_called
        policy_called = True
        return AnswerResponse(
            answer=f"Policy answer.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    async def fake_build_dispute_response(case_id: str, question: str, stage: ChatStage):
        nonlocal dispute_called
        dispute_called = True
        return AIResponse(
            text=f"Dispute answer.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            trigger=AITrigger.DISPUTE,
            metadata={"stage": stage.value},
        )

    async def fake_explain_deadlines_for_case(case_id: str, *, stage: ChatStage):
        return AIResponse(
            text=f"Deadline overview based on saved case dates.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            trigger=AITrigger.DEADLINE,
            metadata={"stage": stage.value, "deadline_intent": "explainer"},
        )

    monkeypatch.setattr(chat_ai_service, "answer_policy_question", fake_answer_policy_question)
    monkeypatch.setattr(chat_ai_service, "_build_dispute_response", fake_build_dispute_response)
    monkeypatch.setattr(chat_ai_service, "explain_deadlines_for_case", fake_explain_deadlines_for_case)

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="@AI what deadlines should I know after the insurer denied my claim?",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.DEADLINE
    assert response.metadata["stage"] == ChatStage.STAGE_1.value
    assert response.metadata["deadline_intent"] == "explainer"
    assert "Deadline overview" in response.text
    assert policy_called is False
    assert dispute_called is False


async def test_handle_chat_event_deadline_mention_returns_friendly_message_for_missing_case(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    async def fake_explain_deadlines_for_case(case_id: str, *, stage: ChatStage):
        raise KeyError(case_id)

    monkeypatch.setattr(chat_ai_service, "explain_deadlines_for_case", fake_explain_deadlines_for_case)

    event = ChatEvent(
        case_id="missing-case",
        sender_role="owner",
        message_text="@AI what deadlines should I know for this claim?",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.DEADLINE
    assert response.metadata["deadline_intent"] == "explainer_missing_case"
    assert "could not find the saved case data" in response.text


async def test_handle_chat_event_deadline_fallback_when_no_mention_or_dispute(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    async def fake_deadline_alert(case_id: str, *, stage: ChatStage):
        return AIResponse(
            text=f"Deadline reminder: the saved claim notice date is close to the acknowledgment deadline.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            trigger=AITrigger.DEADLINE,
            metadata={"stage": stage.value, "deadline_type": "acknowledgment"},
        )

    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", fake_deadline_alert)

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="Just checking in on the claim.",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is not None
    assert response.trigger == AITrigger.DEADLINE
    assert response.metadata["stage"] == ChatStage.STAGE_1.value
    assert response.metadata["deadline_type"] == "acknowledgment"


async def test_handle_chat_event_participant_joined_should_not_invoke_deadline_alert(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    deadline_called = False

    async def fake_deadline_alert(case_id: str, *, stage: ChatStage):
        nonlocal deadline_called
        deadline_called = True
        return None

    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", fake_deadline_alert)

    event = ChatEvent(
        case_id="case-1",
        sender_role="system",
        message_text="",
        participants=[
            Participant(user_id="1", role="owner"),
            Participant(user_id="2", role="adjuster"),
        ],
        invite_sent=True,
        trigger=ChatEventTrigger.PARTICIPANT_JOINED,
    )

    await chat_ai_service.handle_chat_event(event)
    # PARTICIPANT_JOINED should either be handled with a stage-transition message
    # or short-circuit before the ambient deadline poll. It should not silently
    # piggy-back on maybe_get_deadline_alert.
    assert deadline_called is False


async def test_handle_chat_event_policy_indexed_stage_3_should_not_invoke_deadline_alert(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    deadline_called = False

    async def fake_deadline_alert(case_id: str, *, stage: ChatStage):
        nonlocal deadline_called
        deadline_called = True
        return None

    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", fake_deadline_alert)

    event = ChatEvent(
        case_id="case-1",
        sender_role="system",
        message_text="",
        participants=[
            Participant(user_id="1", role="owner"),
            Participant(user_id="2", role="adjuster"),
        ],
        invite_sent=True,
        trigger=ChatEventTrigger.POLICY_INDEXED,
    )

    await chat_ai_service.handle_chat_event(event)
    assert deadline_called is False


async def test_handle_chat_event_soft_signal_non_mention_does_not_interject_when_classifier_is_negative(monkeypatch) -> None:
    from ai.chat import chat_ai_service

    policy_called = False

    async def fake_classify_dispute(message_text: str):
        return DisputeClassification(
            is_dispute=False,
            dispute_type="NOT_DISPUTE",
            recommended_statute=None,
            rationale="Not a dispute after review.",
        )

    async def fake_answer_policy_question(case_id: str, question: str):
        nonlocal policy_called
        policy_called = True
        return AnswerResponse(
            answer=f"Policy answer.\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    monkeypatch.setattr(chat_ai_service, "classify_dispute", fake_classify_dispute)
    monkeypatch.setattr(chat_ai_service, "answer_policy_question", fake_answer_policy_question)
    monkeypatch.setattr(chat_ai_service, "maybe_get_deadline_alert", AsyncMock(return_value=None))

    event = ChatEvent(
        case_id="case-1",
        sender_role="owner",
        message_text="I disagree and the insurer delay is frustrating.",
        participants=[Participant(user_id="1", role="owner")],
        invite_sent=False,
        trigger=ChatEventTrigger.MESSAGE,
    )

    response = await chat_ai_service.handle_chat_event(event)
    assert response is None
    assert policy_called is False

from models.ai_types import AITrigger, AnswerResponse, ChatEvent, ChatEventTrigger, ChatStage, Participant


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

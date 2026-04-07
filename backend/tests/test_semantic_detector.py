from types import SimpleNamespace

from ai.dispute import semantic_detector


def _client_with_content(content: str | None, calls: list[dict[str, object]] | None = None):
    class _FakeCompletions:
        async def create(self, **kwargs):
            if calls is not None:
                calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    return SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))


async def test_classify_dispute_uses_configured_model_and_reasoning_effort(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    client = _client_with_content(
        '{"dispute_type":"DELAY","is_dispute":true,"rationale":"Delay complaint."}',
        calls,
    )

    monkeypatch.setattr(semantic_detector.ai_config, "classification_model", "gpt-5.4-mini")
    monkeypatch.setattr(semantic_detector.ai_config, "classification_reasoning_effort", "xhigh")

    result = await semantic_detector.classify_dispute("They still have not responded to my claim.", client=client)

    assert result.is_dispute is True
    assert result.dispute_type == "DELAY"
    assert calls[0]["model"] == "gpt-5.4-mini"
    assert calls[0]["reasoning_effort"] == "xhigh"


async def test_classify_dispute_maps_amount_statute() -> None:
    client = _client_with_content('{"dispute_type":"AMOUNT","is_dispute":true,"rationale":"Low estimate."}')

    result = await semantic_detector.classify_dispute("The settlement amount is too low.", client=client)

    assert result.is_dispute is True
    assert result.dispute_type == "AMOUNT"
    assert result.recommended_statute == "10 CCR §2695.8"
    assert result.rationale == "Low estimate."


async def test_classify_dispute_not_dispute_label_overrides_true_flag() -> None:
    client = _client_with_content('{"dispute_type":"NOT_DISPUTE","is_dispute":true,"rationale":"No dispute."}')

    result = await semantic_detector.classify_dispute("Can you summarize my deductible?", client=client)

    assert result.is_dispute is False
    assert result.dispute_type == "NOT_DISPUTE"
    assert result.recommended_statute is None


async def test_classify_dispute_unknown_label_falls_back_to_not_dispute() -> None:
    client = _client_with_content('{"dispute_type":"MAYBE","is_dispute":true,"rationale":"Unknown label."}')

    result = await semantic_detector.classify_dispute("The insurer delayed everything.", client=client)

    assert result.is_dispute is False
    assert result.dispute_type == "NOT_DISPUTE"
    assert result.recommended_statute is None


async def test_classify_dispute_malformed_json_falls_back_to_not_dispute() -> None:
    client = _client_with_content("not-json")

    result = await semantic_detector.classify_dispute("The insurer delayed everything.", client=client)

    assert result.is_dispute is False
    assert result.dispute_type == "NOT_DISPUTE"
    assert result.recommended_statute is None

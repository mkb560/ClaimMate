from types import SimpleNamespace

from ai.dispute import semantic_detector


async def test_classify_dispute_uses_configured_model_and_reasoning_effort(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeCompletions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content='{"dispute_type":"DELAY","is_dispute":true,"rationale":"Delay complaint."}'
                        )
                    )
                ]
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))

    monkeypatch.setattr(semantic_detector.ai_config, "classification_model", "gpt-5.4-mini")
    monkeypatch.setattr(semantic_detector.ai_config, "classification_reasoning_effort", "xhigh")

    result = await semantic_detector.classify_dispute("They still have not responded to my claim.", client=client)

    assert result.is_dispute is True
    assert result.dispute_type == "DELAY"
    assert calls[0]["model"] == "gpt-5.4-mini"
    assert calls[0]["reasoning_effort"] == "xhigh"

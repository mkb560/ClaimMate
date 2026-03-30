from types import SimpleNamespace

from ai.ingestion.vector_store import RetrievedChunk
from ai.rag import query_engine
from ai.rag.query_engine import _build_rescue_context, _generate_rescue_answer, _is_not_enough_info


def test_is_not_enough_info_detects_fallback_text() -> None:
    assert _is_not_enough_info(
        "I don't have enough information in the uploaded policy and regulatory materials to answer that confidently."
    ) is True
    assert _is_not_enough_info("The insurer must respond within 15 days. [S1]") is False


def test_build_rescue_context_includes_refs_and_locations() -> None:
    source_index = {
        "S1": RetrievedChunk(
            source_type="kb_b",
            chunk_text="Insurer must acknowledge the claim within 15 calendar days.",
            document_id="ca_reg_2695_5_duties_upon_receipt_of_communications",
            page_num=1,
            section="§ 2695.5",
            metadata={"source_label": "10 CCR 2695.5 Duties Upon Receipt of Communications"},
        )
    }

    context = _build_rescue_context(source_index)

    assert "<snippets>" in context
    assert "[S1]" in context
    assert "Page 1" in context
    assert "Section § 2695.5" in context


async def test_generate_rescue_answer_uses_configured_reasoning_effort(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeCompletions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="Grounded answer. [S1]"))]
            )

    client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))

    monkeypatch.setattr(query_engine.ai_config, "rag_model", "gpt-5.4-mini")
    monkeypatch.setattr(query_engine.ai_config, "rag_reasoning_effort", "xhigh")

    answer = await _generate_rescue_answer(
        question="What is the 15-day rule?",
        source_index={
            "S1": RetrievedChunk(
                source_type="kb_b",
                chunk_text="Insurer must acknowledge the claim within 15 calendar days.",
                document_id="ca_reg_2695_5_duties_upon_receipt_of_communications",
                page_num=1,
                section="§ 2695.5",
                metadata={"source_label": "10 CCR 2695.5 Duties Upon Receipt of Communications"},
            )
        },
        client=client,
    )

    assert answer == "Grounded answer. [S1]"
    assert calls[0]["model"] == "gpt-5.4-mini"
    assert calls[0]["reasoning_effort"] == "xhigh"

from types import SimpleNamespace

from ai.ingestion.vector_store import RetrievedChunk
from ai.rag import query_engine
from ai.rag.query_engine import _build_rescue_context, _generate_rescue_answer, _is_not_enough_info, answer_policy_question


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


async def test_answer_policy_question_prefers_structured_facts_even_when_semantic_search_misses(monkeypatch) -> None:
    async def fake_list_policy_chunks(case_id: str, limit=None):
        return [
            RetrievedChunk(
                source_type="kb_a",
                chunk_text=(
                    "Policy Number: 871890019 Underwritten by: Progressive Select Ins Co "
                    "Policy period: Apr 4, 2026 - Oct 4, 2026"
                ),
                document_id="policy_pdf",
                page_num=1,
                section="PROGRESSIVE",
                metadata={"source_label": "Your Policy (Verification of Insurance.pdf)"},
            )
        ]

    async def fail_generate_answer(**kwargs):
        raise AssertionError("Structured policy fact extraction should answer this question before LLM generation.")

    async def fail_embed_query(question: str) -> list[float]:
        raise AssertionError("Structured policy fact extraction should answer this question before any embedding call.")

    monkeypatch.setattr(query_engine, "_embed_query", fail_embed_query)
    monkeypatch.setattr(query_engine, "list_policy_chunks", fake_list_policy_chunks)
    monkeypatch.setattr(query_engine, "_generate_answer", fail_generate_answer)

    answer = await answer_policy_question("demo-case", "What is the policy number, policy period, and insurer?")

    assert "871890019" in answer.answer
    assert "Apr 4, 2026" in answer.answer
    assert "Progressive Select Ins Co" in answer.answer


async def test_answer_policy_question_prefers_structured_regulatory_rule_without_embedding(monkeypatch) -> None:
    async def fake_list_kb_b_chunks(*, limit=None, document_ids=None):
        return [
            RetrievedChunk(
                source_type="kb_b",
                chunk_text=(
                    "Upon receiving notice of claim, every insurer shall immediately, but in no event more than "
                    "fifteen (15) calendar days later, do the following unless the notice of claim received is a "
                    "notice of legal action: (1) acknowledge receipt of such notice to the claimant."
                ),
                document_id="ca_reg_2695_5_duties_upon_receipt_of_communications",
                page_num=1,
                section="§ 2695.5",
                metadata={"source_label": "10 CCR 2695.5 Duties Upon Receipt of Communications"},
            ),
            RetrievedChunk(
                source_type="kb_b",
                chunk_text="(3) begin any necessary investigation of the claim.",
                document_id="ca_reg_2695_5_duties_upon_receipt_of_communications",
                page_num=1,
                section="§ 2695.5",
                metadata={"source_label": "10 CCR 2695.5 Duties Upon Receipt of Communications"},
            ),
        ]

    async def fail_embed_query(question: str) -> list[float]:
        raise AssertionError("Structured regulatory extraction should answer this question before any embedding call.")

    async def fail_generate_answer(**kwargs):
        raise AssertionError("Structured regulatory extraction should answer this question before LLM generation.")

    monkeypatch.setattr(query_engine, "list_kb_b_chunks", fake_list_kb_b_chunks)
    monkeypatch.setattr(query_engine, "_embed_query", fail_embed_query)
    monkeypatch.setattr(query_engine, "_generate_answer", fail_generate_answer)

    answer = await answer_policy_question("demo-case", "What is the 15-day acknowledgment rule for a California claim?")

    assert "15 calendar days" in answer.answer
    assert "acknowledge receipt" in answer.answer
    assert "begin any necessary investigation" in answer.answer

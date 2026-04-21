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


async def test_answer_policy_question_prefers_extended_structured_policy_facts_without_embedding(monkeypatch) -> None:
    async def fake_list_policy_chunks(case_id: str, limit=None):
        return [
            RetrievedChunk(
                source_type="kb_a",
                chunk_text=(
                    "Coverage detail for 2024 Hyundai Elantra\n"
                    "Automobile Liability Insurance Not applicable $1,235.12\n"
                    "Bodily Injury $50,000 each person\n$100,000 each occurrence\n"
                    "Property Damage $50,000 each occurrence\n"
                    "Rental Reimbursement Not purchased*\n"
                ),
                document_id="policy_pdf",
                page_num=2,
                section="COVERAGE DETAIL",
                metadata={"source_label": "Your Policy (TEMP_PDF_FILE.pdf)"},
            )
        ]

    async def fail_generate_answer(**kwargs):
        raise AssertionError("Structured policy fact extraction should answer this question before LLM generation.")

    async def fail_embed_query(question: str) -> list[float]:
        raise AssertionError("Structured policy fact extraction should answer this question before any embedding call.")

    monkeypatch.setattr(query_engine, "_embed_query", fail_embed_query)
    monkeypatch.setattr(query_engine, "list_policy_chunks", fake_list_policy_chunks)
    monkeypatch.setattr(query_engine, "_generate_answer", fail_generate_answer)

    answer = await answer_policy_question("demo-case", "What are the liability limits, and is rental reimbursement purchased?")

    assert "$50,000 each person" in answer.answer
    assert "Rental Reimbursement" in answer.answer
    assert "Not purchased" in answer.answer


async def test_answer_policy_question_summarizes_policy_without_semantic_search(monkeypatch) -> None:
    async def fake_list_policy_chunks(case_id: str, limit=None):
        return [
            RetrievedChunk(
                source_type="kb_a",
                chunk_text=(
                    "Policyholders: Mingtao Owner\n"
                    "Policy number: 804 448 188\n"
                    "Policy period: Apr 4, 2025 - Oct 4, 2025\n"
                    "Underwritten by: Allstate Vehicle and Property Insurance Company"
                ),
                document_id="policy_pdf",
                page_num=1,
                section="DECLARATIONS",
                metadata={"source_label": "Your Policy (TEMP_PDF_FILE 2.pdf)"},
            ),
            RetrievedChunk(
                source_type="kb_a",
                chunk_text=(
                    "Coverage detail for 2024 Hyundai Elantra\n"
                    "Automobile Liability Insurance\n"
                    "Bodily Injury $50,000 each person\n$100,000 each occurrence\n"
                    "Property Damage $50,000 each occurrence\n"
                    "Rental Reimbursement Not purchased*"
                ),
                document_id="policy_pdf",
                page_num=2,
                section="COVERAGE DETAIL",
                metadata={"source_label": "Your Policy (TEMP_PDF_FILE 2.pdf)"},
            ),
            RetrievedChunk(
                source_type="kb_a",
                chunk_text=(
                    "The following change(s) are effective as of 05/28/2025: "
                    "Added Identity Theft Expenses Coverage. Your discount savings for this policy period are: $123.45"
                ),
                document_id="policy_pdf",
                page_num=3,
                section="POLICY CHANGE",
                metadata={"source_label": "Your Policy (TEMP_PDF_FILE 2.pdf)"},
            ),
        ]

    async def fail_embed_query(question: str) -> list[float]:
        raise AssertionError("Policy summary questions should not need semantic search.")

    async def fail_generate_answer(**kwargs):
        raise AssertionError("Policy summary questions should be answered deterministically.")

    monkeypatch.setattr(query_engine, "list_policy_chunks", fake_list_policy_chunks)
    monkeypatch.setattr(query_engine, "_embed_query", fail_embed_query)
    monkeypatch.setattr(query_engine, "_generate_answer", fail_generate_answer)

    answer = await answer_policy_question("demo-case", "Can you summarize my policy in 3 bullet points?")

    assert "Here are the main policy points I would pay attention to" in answer.answer
    assert answer.answer.count("\n1. ") == 1
    assert answer.answer.count("\n2. ") == 1
    assert answer.answer.count("\n3. ") == 1
    assert "804 448 188" in answer.answer
    assert "$50,000 each person" in answer.answer
    assert "05/28/2025" in answer.answer
    assert "Policy identity:" in answer.answer
    assert "Core coverage snapshot:" in answer.answer
    assert "Important flags:" in answer.answer
    assert len(answer.citations) >= 3


async def test_answer_policy_question_injects_saved_case_context_as_citable_source(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class _FakeCompletions:
        async def create(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content="The saved accident context says the crash happened near USC. [S1]"
                        )
                    )
                ]
            )

    async def fake_embed_query(question: str) -> list[float]:
        return [0.0, 0.1]

    async def fake_search_case_chunks(case_id: str, query_embedding: list[float], top_k=None):
        return [
            RetrievedChunk(
                source_type="kb_a",
                chunk_text="Collision coverage applies subject to policy terms.",
                document_id="policy_pdf",
                page_num=4,
                section="COVERAGE DETAIL",
                metadata={"source_label": "Your Policy (policy.pdf)"},
            )
        ]

    async def fake_search_kb_b_chunks(query_embedding: list[float], *, top_k=None, document_ids=None):
        return []

    async def fake_list_policy_chunks(case_id: str, limit=None):
        return await fake_search_case_chunks(case_id, [0.0, 0.1])

    monkeypatch.setattr(query_engine, "_embed_query", fake_embed_query)
    monkeypatch.setattr(query_engine, "search_case_chunks", fake_search_case_chunks)
    monkeypatch.setattr(query_engine, "search_kb_b_chunks", fake_search_kb_b_chunks)
    monkeypatch.setattr(query_engine, "list_policy_chunks", fake_list_policy_chunks)

    answer = await answer_policy_question(
        "demo-case",
        "Based on my accident, what should I know about coverage?",
        client=SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions())),
        case_context={
            "chat_context": {
                "summary": "Rear-end crash near USC.",
                "key_facts": ["Location: 1200 S Figueroa St", "Police called: Yes"],
                "party_comparison_rows": [
                    {"field_label": "Vehicle", "owner_value": "2024 Hyundai", "other_party_value": "2019 Toyota"}
                ],
            }
        },
    )

    assert "Saved Accident Context" in calls[0]["messages"][1]["content"]
    assert "Rear-end crash near USC" in calls[0]["messages"][1]["content"]
    assert answer.citations[0].source_type == "case_context"
    assert answer.citations[0].source_label == "Saved Accident Context"


async def test_answer_policy_question_builds_accident_coverage_checklist_without_llm(monkeypatch) -> None:
    async def fake_list_policy_chunks(case_id: str, limit=None):
        return [
            RetrievedChunk(
                source_type="kb_a",
                chunk_text=(
                    "Coverage detail for 2024 Hyundai Elantra\n"
                    "Automobile Liability Insurance\n"
                    "Bodily Injury $50,000 each person\n$100,000 each occurrence\n"
                    "Property Damage $50,000 each occurrence\n"
                    "Auto Collision Insurance $500 deductible\n"
                    "Auto Comprehensive Insurance Not purchased\n"
                    "Rental Reimbursement Not purchased*"
                ),
                document_id="policy_pdf",
                page_num=2,
                section="COVERAGE DETAIL",
                metadata={"source_label": "Your Policy (policy.pdf)"},
            )
        ]

    async def fail_embed_query(question: str) -> list[float]:
        raise AssertionError("Accident coverage checklist should not require semantic search.")

    async def fail_generate_answer(**kwargs):
        raise AssertionError("Accident coverage checklist should be answered deterministically.")

    monkeypatch.setattr(query_engine, "list_policy_chunks", fake_list_policy_chunks)
    monkeypatch.setattr(query_engine, "_embed_query", fail_embed_query)
    monkeypatch.setattr(query_engine, "_generate_answer", fail_generate_answer)

    answer = await answer_policy_question(
        "demo-case",
        "Based on my accident, what policy coverage should I check?",
        case_context={
            "chat_context": {
                "summary": "Rear-end crash near USC.",
                "key_facts": ["Location: 1200 S Figueroa St"],
            }
        },
    )

    assert "Based on the saved accident context" in answer.answer
    assert "Rear-end crash near USC" in answer.answer
    assert "collision coverage" in answer.answer.lower()
    assert "Rental Reimbursement" in answer.answer
    assert answer.citations[0].source_type == "case_context"
    assert any(citation.source_type == "kb_a" for citation in answer.citations)


async def test_generate_answer_uses_rescue_when_initial_answer_has_no_citations() -> None:
    responses = iter(
        [
            "Your policy includes rental reimbursement.",
            "The policy lists Rental Reimbursement as Not purchased. [S1]",
        ]
    )

    class _FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(responses)))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))
    policy_chunk = RetrievedChunk(
        source_type="kb_a",
        chunk_text="Rental Reimbursement Not purchased*",
        document_id="policy_pdf",
        page_num=2,
        section="COVERAGE DETAIL",
        metadata={"source_label": "Your Policy (TEMP_PDF_FILE.pdf)"},
    )

    answer = await query_engine._generate_answer(
        question="Does this policy cover rental reimbursement?",
        policy_chunks=[policy_chunk],
        regulatory_chunks=[],
        client=client,
        system_prompt="test",
    )

    assert "Not purchased" in answer.answer
    assert len(answer.citations) == 1


async def test_generate_answer_falls_back_to_not_enough_info_when_citations_are_missing_after_rescue() -> None:
    responses = iter(
        [
            "Your policy includes rental reimbursement.",
            "Still no citations in this answer.",
        ]
    )

    class _FakeCompletions:
        async def create(self, **kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(responses)))])

    client = SimpleNamespace(chat=SimpleNamespace(completions=_FakeCompletions()))
    policy_chunk = RetrievedChunk(
        source_type="kb_a",
        chunk_text="Rental Reimbursement Not purchased*",
        document_id="policy_pdf",
        page_num=2,
        section="COVERAGE DETAIL",
        metadata={"source_label": "Your Policy (TEMP_PDF_FILE.pdf)"},
    )

    answer = await query_engine._generate_answer(
        question="Does this policy cover rental reimbursement?",
        policy_chunks=[policy_chunk],
        regulatory_chunks=[],
        client=client,
        system_prompt="test",
    )

    assert query_engine.NOT_ENOUGH_INFO_MESSAGE in answer.answer
    assert len(answer.citations) == 1

from ai.ingestion.vector_store import RetrievedChunk
from ai.policy.fact_extractor import answer_structured_policy_question, extract_policy_facts


def test_extract_policyholders_and_policy_number_from_allstate_style_chunk() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text=(
                "Policyholder(s)\nAnlan Cai\nMingtao Ding\n55 E Hntngtn Dr #219\n"
                "Policy number\n804 448 188\n"
            ),
            document_id="policy_pdf",
            page_num=1,
            section=None,
            metadata={"source_label": "Your Policy (TEMP_PDF_FILE.pdf)"},
        )
    ]

    facts = extract_policy_facts(chunks)

    assert facts["policyholders"][0].value == "Anlan Cai, Mingtao Ding"
    assert facts["policy_number"][0].value == "804 448 188"


def test_answer_structured_policy_question_prefers_deterministic_fact_answer() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text="Policyholders: Mingtao Ding Yizhan Huang Policy Number: 871890019",
            document_id="policy_pdf",
            page_num=1,
            section="PROGRESSIVE",
            metadata={"source_label": "Your Policy (Verification of Insurance.pdf)"},
        )
    ]

    answer = answer_structured_policy_question("Who are the policyholders and what is the policy number?", chunks)

    assert answer is not None
    assert "Mingtao Ding" in answer.answer
    assert "871890019" in answer.answer
    assert len(answer.citations) >= 1

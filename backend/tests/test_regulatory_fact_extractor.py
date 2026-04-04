from ai.ingestion.vector_store import RetrievedChunk
from ai.rag.regulatory_fact_extractor import answer_structured_regulatory_question, is_structured_regulatory_question


def test_is_structured_regulatory_question_detects_15_day_claim_questions() -> None:
    assert is_structured_regulatory_question("What is the 15-day acknowledgment rule for a California claim?") is True
    assert is_structured_regulatory_question(
        "What should the insurer do within 15 days after receiving notice of claim?"
    ) is True
    assert is_structured_regulatory_question("What optional coverage is highlighted in this renewal offer?") is False


def test_answer_structured_regulatory_question_builds_grounded_answer() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_b",
            chunk_text=(
                "Upon receiving notice of claim, every insurer shall immediately, but in no event more than "
                "fifteen (15) calendar days later, do the following unless the notice of claim received is a "
                "notice of legal action: (1) acknowledge receipt of such notice to the claimant unless payment "
                "is made within that period of time."
            ),
            document_id="ca_reg_2695_5_duties_upon_receipt_of_communications",
            page_num=1,
            section="§ 2695.5",
            metadata={"source_label": "10 CCR 2695.5 Duties Upon Receipt of Communications"},
        ),
        RetrievedChunk(
            source_type="kb_b",
            chunk_text=(
                "(2) provide to the claimant necessary forms, instructions, and reasonable assistance; "
                "(3) begin any necessary investigation of the claim."
            ),
            document_id="ca_reg_2695_5_duties_upon_receipt_of_communications",
            page_num=1,
            section="§ 2695.5",
            metadata={"source_label": "10 CCR 2695.5 Duties Upon Receipt of Communications"},
        ),
    ]

    answer = answer_structured_regulatory_question(
        "What is the 15-day acknowledgment rule for a California claim?",
        chunks,
    )

    assert answer is not None
    assert "15 calendar days" in answer.answer
    assert "acknowledge receipt" in answer.answer
    assert "begin any necessary investigation" in answer.answer
    assert answer.citations
    assert answer.citations[0].source_type == "kb_b"

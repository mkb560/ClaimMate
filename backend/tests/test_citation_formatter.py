from ai.ingestion.vector_store import RetrievedChunk
from ai.rag.citation_formatter import build_context_sections, citations_from_answer, fallback_citations, source_label_for_chunk


def test_citations_from_answer_reads_source_refs() -> None:
    policy_chunk = RetrievedChunk(
        source_type="kb_a",
        chunk_text="Collision deductible is $500.",
        document_id="policy_pdf",
        page_num=3,
        section="COVERAGE",
    )
    regulatory_chunk = RetrievedChunk(
        source_type="kb_b",
        chunk_text="Insurers must respond within 15 days.",
        document_id="ca_fair_claims",
        page_num=1,
        section="§2695.5",
    )
    _, source_index = build_context_sections([policy_chunk], [regulatory_chunk])

    citations = citations_from_answer("Your deductible is $500. [S1] The regulation says 15 days. [S2]", source_index)

    assert [citation.document_id for citation in citations] == ["policy_pdf", "ca_fair_claims"]


def test_fallback_citations_deduplicate_by_location() -> None:
    chunks = [
        RetrievedChunk(
            source_type="kb_a",
            chunk_text="A",
            document_id="policy_pdf",
            page_num=1,
            section="DECLARATIONS",
        ),
        RetrievedChunk(
            source_type="kb_a",
            chunk_text="B",
            document_id="policy_pdf",
            page_num=1,
            section="DECLARATIONS",
        ),
    ]
    citations = fallback_citations(chunks)
    assert len(citations) == 1


def test_source_label_uses_chunk_metadata_when_available() -> None:
    chunk = RetrievedChunk(
        source_type="kb_b",
        chunk_text="Insurers must acknowledge receipt.",
        document_id="ca_reg_2695_5_duties_upon_receipt_of_communications",
        page_num=1,
        section="2695.5",
        metadata={"source_label": "Custom Regulatory Label"},
    )

    assert source_label_for_chunk(chunk) == "Custom Regulatory Label"


def test_source_label_uses_policy_file_name_from_metadata() -> None:
    chunk = RetrievedChunk(
        source_type="kb_a",
        chunk_text="Deductible is $500.",
        document_id="policy_pdf",
        page_num=2,
        section="DECLARATIONS",
        metadata={"source_label": "Your Policy (sample-policy.pdf)"},
    )

    assert source_label_for_chunk(chunk) == "Your Policy (sample-policy.pdf)"

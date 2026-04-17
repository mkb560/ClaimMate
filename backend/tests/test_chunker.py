from ai.ingestion.chunker import _detect_section, _slice_text


def test_detect_section_skips_generic_page_boilerplate() -> None:
    text = "PAGE 1 OF 3\nALLSTATE INSURANCE COMPANY\nCOVERAGE DETAIL\nRental Reimbursement Not purchased*"

    assert _detect_section(text) == "COVERAGE DETAIL"


def test_slice_text_keeps_last_non_whitespace_chunk() -> None:
    text = "alpha beta gamma delta epsilon"
    chunks = _slice_text(text, chunk_size=50, overlap=10)

    assert chunks
    assert any("epsilon" in chunk for chunk in chunks)

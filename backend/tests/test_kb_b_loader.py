from pathlib import Path

from ai.ingestion.kb_b_loader import build_local_kb_b_sources


def test_build_local_kb_b_sources_discovers_supported_files(tmp_path: Path) -> None:
    docs_dir = tmp_path / "claimmate_rag_docs"
    regs_dir = docs_dir / "02_ca_regulations"
    guides_dir = docs_dir / "03_consumer_guides"
    regs_dir.mkdir(parents=True)
    guides_dir.mkdir(parents=True)

    (regs_dir / "ca_reg_2695_5_duties_upon_receipt_of_communications.pdf").write_bytes(b"%PDF-1.4")
    (guides_dir / "naic_consumer_guide_auto_claims.pdf").write_bytes(b"%PDF-1.4")
    (docs_dir / "metadata_schema.json").write_text("{}", encoding="utf-8")
    (docs_dir / ".DS_Store").write_bytes(b"ignored")

    sources = build_local_kb_b_sources(docs_dir)

    assert [source.document_id for source in sources] == [
        "ca_reg_2695_5_duties_upon_receipt_of_communications",
        "naic_consumer_guide_auto_claims",
    ]
    assert sources[0].source_label == "10 CCR 2695.5 Duties Upon Receipt of Communications"
    assert sources[1].source_label == "NAIC Consumer Guide to Auto Claims"

from __future__ import annotations

from pathlib import Path

import pytest
from ai.ingestion.vector_store import RetrievedChunk


def test_resolve_demo_policy_seed_uses_fixed_case_id_default() -> None:
    from app.demo_policy_service import resolve_demo_policy_seed

    seed = resolve_demo_policy_seed("allstate-change-2025-05")

    assert seed.key == "allstate-change"
    assert seed.filename == "TEMP_PDF_FILE.pdf"


def test_resolve_demo_policy_seed_requires_explicit_key_for_custom_case() -> None:
    from app.demo_policy_service import resolve_demo_policy_seed

    with pytest.raises(LookupError):
        resolve_demo_policy_seed("custom-demo-case")


def test_list_demo_policies_returns_catalog() -> None:
    from app.demo_policy_service import list_demo_policies

    catalog = list_demo_policies()

    assert [item["policy_key"] for item in catalog] == [
        "allstate-change",
        "allstate-renewal",
        "progressive-verification",
    ]
    assert catalog[0]["default_case_id"] == "allstate-change-2025-05"


async def test_get_policy_status_matches_demo_policy_from_stored_chunks(monkeypatch) -> None:
    from app import demo_policy_service

    async def fake_list_policy_chunks(case_id: str, *, limit=None):
        assert case_id == "allstate-renewal-2025-08"
        assert limit is None
        return [
            RetrievedChunk(
                source_type="kb_a",
                chunk_text="Page 1 policy text",
                document_id="policy_pdf",
                page_num=1,
                section=None,
                metadata={
                    "source_label": "Your Policy (TEMP_PDF_FILE 2.pdf)",
                    "policy_path": "/tmp/TEMP_PDF_FILE 2.pdf",
                },
            ),
            RetrievedChunk(
                source_type="kb_a",
                chunk_text="Page 2 policy text",
                document_id="policy_pdf",
                page_num=2,
                section=None,
                metadata={
                    "source_label": "Your Policy (TEMP_PDF_FILE 2.pdf)",
                    "policy_path": "/tmp/TEMP_PDF_FILE 2.pdf",
                },
            ),
        ]

    monkeypatch.setattr(demo_policy_service, "list_policy_chunks", fake_list_policy_chunks)

    result = await demo_policy_service.get_policy_status("allstate-renewal-2025-08")

    assert result == {
        "case_id": "allstate-renewal-2025-08",
        "has_policy": True,
        "chunk_count": 2,
        "source_label": "Your Policy (TEMP_PDF_FILE 2.pdf)",
        "filename": "TEMP_PDF_FILE 2.pdf",
        "demo_policy": {
            "policy_key": "allstate-renewal",
            "default_case_id": "allstate-renewal-2025-08",
            "label": "Allstate renewal packet",
            "filename": "TEMP_PDF_FILE 2.pdf",
            "sample_questions": [
                "What kind of insurance packet is this and who are the policyholders?",
                "What optional coverage is highlighted in this renewal offer?",
                "What should the insurer do within 15 days after receiving notice of claim?",
            ],
        },
    }


async def test_get_policy_status_returns_empty_state_when_case_has_no_chunks(monkeypatch) -> None:
    from app import demo_policy_service

    async def fake_list_policy_chunks(case_id: str, *, limit=None):
        assert case_id == "demo-case"
        assert limit is None
        return []

    monkeypatch.setattr(demo_policy_service, "list_policy_chunks", fake_list_policy_chunks)

    result = await demo_policy_service.get_policy_status("demo-case")

    assert result == {
        "case_id": "demo-case",
        "has_policy": False,
        "chunk_count": 0,
        "source_label": None,
        "filename": None,
        "demo_policy": None,
    }


async def test_seed_demo_policy_copies_pdf_and_indexes_requested_seed(monkeypatch, tmp_path: Path) -> None:
    from app import demo_policy_service

    source_root = tmp_path / "demo_policy_pdfs"
    source_root.mkdir(parents=True, exist_ok=True)
    source_file = source_root / "Verification of Insurance.pdf"
    source_file.write_bytes(b"%PDF-1.4 demo policy bytes")

    policy_storage_root = tmp_path / "policies"
    captured: dict[str, object] = {}

    async def fake_ensure_case(case_id: str) -> None:
        captured["case_id"] = case_id

    async def fake_ingest_local_policy_file(pdf_path: str | Path, case_id: str) -> int:
        path = Path(pdf_path)
        captured["ingest_path"] = path
        captured["ingest_case_id"] = case_id
        captured["saved_bytes"] = path.read_bytes()
        return 4

    monkeypatch.setattr(demo_policy_service, "DEMO_POLICY_ROOT", source_root)
    monkeypatch.setattr(demo_policy_service, "LOCAL_POLICY_STORAGE_ROOT", policy_storage_root)
    monkeypatch.setattr(demo_policy_service.case_service, "ensure_case", fake_ensure_case)
    monkeypatch.setattr(demo_policy_service, "ingest_local_policy_file", fake_ingest_local_policy_file)

    result = await demo_policy_service.seed_demo_policy("custom-demo-case", "progressive_verification")

    assert result == {
        "case_id": "custom-demo-case",
        "policy_key": "progressive-verification",
        "default_case_id": "progressive-verification-2026-03",
        "label": "Progressive verification letter",
        "filename": "Verification of Insurance.pdf",
        "chunk_count": 4,
        "status": "indexed",
        "sample_questions": [
            "What is the policy number, policy period, and insurer?",
            "Does this document say it is a full insurance policy or only verification of insurance?",
            "What is the 15-day acknowledgment rule for a California claim?",
        ],
    }
    assert captured["case_id"] == "custom-demo-case"
    assert captured["ingest_case_id"] == "custom-demo-case"
    assert captured["saved_bytes"] == b"%PDF-1.4 demo policy bytes"
    saved_path = captured["ingest_path"]
    assert isinstance(saved_path, Path)
    assert saved_path == policy_storage_root / "custom-demo-case" / "Verification of Insurance.pdf"

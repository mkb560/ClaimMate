from __future__ import annotations

from pathlib import Path

import pytest


def test_resolve_demo_policy_seed_uses_fixed_case_id_default() -> None:
    from app.demo_policy_service import resolve_demo_policy_seed

    seed = resolve_demo_policy_seed("allstate-change-2025-05")

    assert seed.key == "allstate-change"
    assert seed.filename == "TEMP_PDF_FILE.pdf"


def test_resolve_demo_policy_seed_requires_explicit_key_for_custom_case() -> None:
    from app.demo_policy_service import resolve_demo_policy_seed

    with pytest.raises(LookupError):
        resolve_demo_policy_seed("custom-demo-case")


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


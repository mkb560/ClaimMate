from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ai.ingestion.ingest_policy import ingest_local_policy_file
from app import case_service
from app.paths import LOCAL_POLICY_STORAGE_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_POLICY_ROOT = REPO_ROOT / "demo_policy_pdfs"


@dataclass(frozen=True, slots=True)
class DemoPolicySeed:
    key: str
    default_case_id: str
    filename: str
    label: str
    sample_questions: tuple[str, ...]


DEMO_POLICY_SEEDS: tuple[DemoPolicySeed, ...] = (
    DemoPolicySeed(
        key="allstate-change",
        default_case_id="allstate-change-2025-05",
        filename="TEMP_PDF_FILE.pdf",
        label="Allstate policy change packet",
        sample_questions=(
            "Who are the policyholders and what is the policy number?",
            "What policy change is confirmed and when is it effective?",
            "What discount savings are listed for this policy period?",
        ),
    ),
    DemoPolicySeed(
        key="allstate-renewal",
        default_case_id="allstate-renewal-2025-08",
        filename="TEMP_PDF_FILE 2.pdf",
        label="Allstate renewal packet",
        sample_questions=(
            "What kind of insurance packet is this and who are the policyholders?",
            "What optional coverage is highlighted in this renewal offer?",
            "What should the insurer do within 15 days after receiving notice of claim?",
        ),
    ),
    DemoPolicySeed(
        key="progressive-verification",
        default_case_id="progressive-verification-2026-03",
        filename="Verification of Insurance.pdf",
        label="Progressive verification letter",
        sample_questions=(
            "What is the policy number, policy period, and insurer?",
            "Does this document say it is a full insurance policy or only verification of insurance?",
            "What is the 15-day acknowledgment rule for a California claim?",
        ),
    ),
)

_SEED_BY_KEY = {seed.key: seed for seed in DEMO_POLICY_SEEDS}
_SEED_BY_CASE_ID = {seed.default_case_id: seed for seed in DEMO_POLICY_SEEDS}
_KEY_ALIASES = {
    seed.key.replace("-", "_"): seed.key for seed in DEMO_POLICY_SEEDS
}


def list_demo_policy_keys() -> list[str]:
    return [seed.key for seed in DEMO_POLICY_SEEDS]


def _normalize_policy_key(policy_key: str) -> str:
    lowered = policy_key.strip().lower()
    return _KEY_ALIASES.get(lowered, lowered)


def resolve_demo_policy_seed(case_id: str, policy_key: str | None = None) -> DemoPolicySeed:
    if policy_key:
        normalized_key = _normalize_policy_key(policy_key)
        if seed := _SEED_BY_KEY.get(normalized_key):
            return seed
        raise KeyError(policy_key)

    if seed := _SEED_BY_CASE_ID.get(case_id):
        return seed
    raise LookupError(case_id)


def _copy_demo_policy(case_id: str, seed: DemoPolicySeed) -> Path:
    source = (DEMO_POLICY_ROOT / seed.filename).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Demo policy PDF not found: {source}")

    target_dir = LOCAL_POLICY_STORAGE_ROOT / case_id
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    shutil.copy2(source, target)
    return target


async def seed_demo_policy(case_id: str, policy_key: str | None = None) -> dict[str, Any]:
    seed = resolve_demo_policy_seed(case_id, policy_key)
    await case_service.ensure_case(case_id)
    saved_path = _copy_demo_policy(case_id, seed)
    chunk_count = await ingest_local_policy_file(saved_path, case_id=case_id)
    return {
        "case_id": case_id,
        "policy_key": seed.key,
        "default_case_id": seed.default_case_id,
        "label": seed.label,
        "filename": saved_path.name,
        "chunk_count": chunk_count,
        "status": "indexed",
        "sample_questions": list(seed.sample_questions),
    }

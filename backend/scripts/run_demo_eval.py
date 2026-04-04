from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

from openai import OpenAIError, RateLimitError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
DEMO_POLICY_ROOT = REPO_ROOT / "demo_policy_pdfs"
DEMO_KB_B_ROOT = REPO_ROOT / "claimmate_rag_docs"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.config import ai_config
from ai.ingestion.ingest_policy import ingest_local_policy_file
from ai.ingestion.kb_b_loader import build_local_kb_b_sources, index_kb_b_sources
from ai.ingestion.vector_store import list_kb_b_chunks, list_policy_chunks
from ai.rag.query_engine import answer_policy_question
from ai.runtime import bootstrap_vector_store, create_ai_engine


@dataclass(frozen=True, slots=True)
class EvalQuestion:
    question: str
    expected_substrings: tuple[str, ...] = ()
    expected_any_groups: tuple[tuple[str, ...], ...] = ()
    min_citations: int = 1
    required_source_types: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EvalCase:
    case_id: str
    label: str
    policy_pdf: str | None
    questions: tuple[EvalQuestion, ...]


@dataclass(slots=True)
class EvalResult:
    case_id: str
    question: str
    passed: bool
    answer: str
    citations: int
    missing_substrings: list[str]
    missing_source_types: list[str]


DEMO_EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        case_id="allstate-change-2025-05",
        label="Allstate policy change packet",
        policy_pdf=str((DEMO_POLICY_ROOT / "TEMP_PDF_FILE.pdf").resolve()),
        questions=(
            EvalQuestion(
                question="Who are the policyholders and what is the policy number?",
                expected_substrings=("804 448 188", "Mingtao", "Anlan"),
                required_source_types=("kb_a",),
            ),
            EvalQuestion(
                question="What policy change is confirmed and when is it effective?",
                expected_substrings=("addition of one or more operators", "05/15/2025"),
                required_source_types=("kb_a",),
            ),
            EvalQuestion(
                question="What discount savings are listed for this policy period?",
                expected_substrings=("$965.29",),
                required_source_types=("kb_a",),
            ),
        ),
    ),
    EvalCase(
        case_id="allstate-renewal-2025-08",
        label="Allstate renewal packet",
        policy_pdf=str((DEMO_POLICY_ROOT / "TEMP_PDF_FILE 2.pdf").resolve()),
        questions=(
            EvalQuestion(
                question="What kind of insurance packet is this and who are the policyholders?",
                expected_substrings=("renewal", "Mingtao", "Anlan"),
                required_source_types=("kb_a",),
            ),
            EvalQuestion(
                question="What optional coverage is highlighted in this renewal offer?",
                expected_substrings=("Identity Theft Expenses Coverage",),
                required_source_types=("kb_a",),
            ),
            EvalQuestion(
                question="What should the insurer do within 15 days after receiving notice of claim?",
                expected_any_groups=(
                    ("15", "15 calendar days"),
                    ("acknowledge", "acknowledgment"),
                    ("investigation", "begin any necessary investigation"),
                ),
                required_source_types=("kb_b",),
            ),
        ),
    ),
    EvalCase(
        case_id="progressive-verification-2026-03",
        label="Progressive verification letter",
        policy_pdf=str((DEMO_POLICY_ROOT / "Verification of Insurance.pdf").resolve()),
        questions=(
            EvalQuestion(
                question="What is the policy number, policy period, and insurer?",
                expected_substrings=("871890019", "Apr 4, 2026", "Oct 4, 2026", "Progressive"),
                required_source_types=("kb_a",),
            ),
            EvalQuestion(
                question="Does this document say it is a full insurance policy or only verification of insurance?",
                expected_substrings=("verification of insurance", "not the full policy"),
                required_source_types=("kb_a",),
            ),
            EvalQuestion(
                question="What is the 15-day acknowledgment rule for a California claim?",
                expected_any_groups=(
                    ("15", "15 calendar days"),
                    ("acknowledge", "acknowledgment"),
                    ("investigation", "begin any necessary investigation"),
                ),
                required_source_types=("kb_b",),
            ),
        ),
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the fixed ClaimMate demo/eval suite.")
    parser.add_argument("--json-out", help="Optional path to write JSON results.")
    parser.add_argument(
        "--ingest-policy",
        action="append",
        default=[],
        metavar="CASE_ID=/absolute/path/to/policy.pdf",
        help="Optionally ingest or refresh a policy PDF before running the suite.",
    )
    return parser.parse_args()


def _parse_ingest_overrides(raw_values: list[str]) -> dict[str, str]:
    overrides: dict[str, str] = {}
    for item in raw_values:
        if "=" not in item:
            raise ValueError(f"Invalid --ingest-policy value: {item}")
        case_id, path = item.split("=", 1)
        overrides[case_id.strip()] = path.strip()
    return overrides


def _passes(
    answer: str,
    *,
    expected_substrings: tuple[str, ...],
    expected_any_groups: tuple[tuple[str, ...], ...] = (),
    citations: int,
    min_citations: int,
) -> tuple[bool, list[str]]:
    lowered = answer.lower()
    missing = [item for item in expected_substrings if item.lower() not in lowered]
    for group in expected_any_groups:
        if not any(option.lower() in lowered for option in group):
            missing.append("one of: " + " / ".join(group))
    return (not missing and citations >= min_citations), missing


def _missing_source_types(*, citation_source_types: set[str], required_source_types: tuple[str, ...]) -> list[str]:
    return [item for item in required_source_types if item not in citation_source_types]


def _resolve_policy_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (REPO_ROOT / path).resolve()
    else:
        path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Policy PDF not found: {path}")
    return path


def _ensure_database_url_configured() -> None:
    if ai_config.database_url:
        return
    raise SystemExit(
        "DATABASE_URL is required for demo eval. "
        "Export it in the shell or add it to backend/.env before running scripts/run_demo_eval.py."
    )


def _render_openai_error(error: OpenAIError) -> str:
    if isinstance(error, RateLimitError):
        return (
            "OpenAI request failed due to quota or rate limit. "
            "Check billing/quota for the configured OPENAI_API_KEY, then rerun scripts/run_demo_eval.py."
        )
    return f"OpenAI request failed during demo eval: {error}"


async def main() -> None:
    args = parse_args()
    ingest_overrides = _parse_ingest_overrides(args.ingest_policy)
    results: list[EvalResult] = []

    _ensure_database_url_configured()
    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        if not await list_kb_b_chunks(limit=1):
            sources = build_local_kb_b_sources(DEMO_KB_B_ROOT)
            if not sources:
                raise RuntimeError(f"No supported KB-B files found in {DEMO_KB_B_ROOT}")
            kb_b_results = await index_kb_b_sources(sources)
            print(f"Indexed {len(kb_b_results)} KB-B document(s) from {DEMO_KB_B_ROOT}.")
        else:
            print(f"Using existing indexed KB-B corpus from {DEMO_KB_B_ROOT}.")

        for case in DEMO_EVAL_CASES:
            override_pdf = ingest_overrides.get(case.case_id)
            policy_pdf = override_pdf or case.policy_pdf
            if policy_pdf:
                resolved_pdf = _resolve_policy_path(policy_pdf)
                should_ingest = bool(override_pdf)
                if not should_ingest:
                    should_ingest = not bool(await list_policy_chunks(case.case_id, limit=1))
                if should_ingest:
                    chunk_count = await ingest_local_policy_file(resolved_pdf, case_id=case.case_id)
                    print(f"Ingested {resolved_pdf.name} into {case.case_id} ({chunk_count} chunk(s)).")
                else:
                    print(f"Using existing indexed policy for {case.case_id} ({resolved_pdf.name}).")

            print(f"===== {case.case_id} | {case.label} =====")
            for item in case.questions:
                answer = await answer_policy_question(case.case_id, item.question)
                passed, missing = _passes(
                    answer.answer,
                    expected_substrings=item.expected_substrings,
                    expected_any_groups=item.expected_any_groups,
                    citations=len(answer.citations),
                    min_citations=item.min_citations,
                )
                missing_source_types = _missing_source_types(
                    citation_source_types={citation.source_type for citation in answer.citations},
                    required_source_types=item.required_source_types,
                )
                passed = passed and not missing_source_types
                status = "PASS" if passed else "FAIL"
                print(f"[{status}] {item.question}")
                print(answer.answer)
                print(f"Citations: {len(answer.citations)}")
                if missing:
                    print("Missing:", ", ".join(missing))
                if missing_source_types:
                    print("Missing citation source types:", ", ".join(missing_source_types))
                print()
                results.append(
                    EvalResult(
                        case_id=case.case_id,
                        question=item.question,
                        passed=passed,
                        answer=answer.answer,
                        citations=len(answer.citations),
                        missing_substrings=missing,
                        missing_source_types=missing_source_types,
                    )
                )
    finally:
        await engine.dispose()

    passed_count = sum(result.passed for result in results)
    print(f"Summary: {passed_count}/{len(results)} passed")

    if args.json_out:
        output_path = Path(args.json_out).expanduser().resolve()
        output_path.write_text(
            json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Saved JSON results to {output_path}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except OpenAIError as error:
        raise SystemExit(_render_openai_error(error)) from error

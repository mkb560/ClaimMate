from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.ingestion.ingest_policy import ingest_local_policy_file
from ai.rag.query_engine import answer_policy_question
from ai.runtime import bootstrap_vector_store, create_ai_engine


@dataclass(frozen=True, slots=True)
class EvalQuestion:
    question: str
    expected_substrings: tuple[str, ...]
    min_citations: int = 1


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


DEMO_EVAL_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        case_id="allstate-change-2025-05",
        label="Allstate policy change packet",
        policy_pdf=None,
        questions=(
            EvalQuestion(
                question="Who are the policyholders and what is the policy number?",
                expected_substrings=("804 448 188", "Mingtao", "Anlan"),
            ),
            EvalQuestion(
                question="What policy change is confirmed and when is it effective?",
                expected_substrings=("addition of one or more operators", "05/15/2025"),
            ),
            EvalQuestion(
                question="What discount savings are listed for this policy period?",
                expected_substrings=("$965.29",),
            ),
        ),
    ),
    EvalCase(
        case_id="allstate-renewal-2025-08",
        label="Allstate renewal packet",
        policy_pdf=None,
        questions=(
            EvalQuestion(
                question="What kind of insurance packet is this and who are the policyholders?",
                expected_substrings=("renewal", "Mingtao", "Anlan"),
            ),
            EvalQuestion(
                question="What optional coverage is highlighted in this renewal offer?",
                expected_substrings=("Identity Theft Expenses Coverage",),
            ),
            EvalQuestion(
                question="What should the insurer do within 15 days after receiving notice of claim?",
                expected_substrings=("15", "acknowledge", "investigation"),
            ),
        ),
    ),
    EvalCase(
        case_id="progressive-verification-2026-03",
        label="Progressive verification letter",
        policy_pdf=None,
        questions=(
            EvalQuestion(
                question="What is the policy number, policy period, and insurer?",
                expected_substrings=("871890019", "Apr 4, 2026", "Oct 4, 2026", "Progressive"),
            ),
            EvalQuestion(
                question="Does this document say it is a full insurance policy or only verification of insurance?",
                expected_substrings=("verification of insurance", "not"),
            ),
            EvalQuestion(
                question="What is the 15-day acknowledgment rule for a California claim?",
                expected_substrings=("15", "acknowledge", "investigation"),
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


def _passes(answer: str, *, expected_substrings: tuple[str, ...], citations: int, min_citations: int) -> tuple[bool, list[str]]:
    lowered = answer.lower()
    missing = [item for item in expected_substrings if item.lower() not in lowered]
    return (not missing and citations >= min_citations), missing


async def main() -> None:
    args = parse_args()
    ingest_overrides = _parse_ingest_overrides(args.ingest_policy)
    results: list[EvalResult] = []

    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        for case in DEMO_EVAL_CASES:
            policy_pdf = ingest_overrides.get(case.case_id) or case.policy_pdf
            if policy_pdf:
                await ingest_local_policy_file(policy_pdf, case_id=case.case_id)

            print(f"===== {case.case_id} | {case.label} =====")
            for item in case.questions:
                answer = await answer_policy_question(case.case_id, item.question)
                passed, missing = _passes(
                    answer.answer,
                    expected_substrings=item.expected_substrings,
                    citations=len(answer.citations),
                    min_citations=item.min_citations,
                )
                status = "PASS" if passed else "FAIL"
                print(f"[{status}] {item.question}")
                print(answer.answer)
                print(f"Citations: {len(answer.citations)}")
                if missing:
                    print("Missing:", ", ".join(missing))
                print()
                results.append(
                    EvalResult(
                        case_id=case.case_id,
                        question=item.question,
                        passed=passed,
                        answer=answer.answer,
                        citations=len(answer.citations),
                        missing_substrings=missing,
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
    asyncio.run(main())

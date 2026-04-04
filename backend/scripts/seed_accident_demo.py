from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEMO_OUTPUT_ROOT = BACKEND_ROOT / ".local_data" / "demo_cases"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.config import ai_config
from ai.runtime import bootstrap_vector_store, create_ai_engine
from app.demo_case_service import seed_demo_accident_case
from app.demo_seed_data import DEMO_ACCIDENT_CASE_ID


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed a stable accident/chat demo case and export sample JSON.")
    parser.add_argument("--case-id", default=DEMO_ACCIDENT_CASE_ID, help="Stable case_id to seed.")
    parser.add_argument(
        "--output-dir",
        help="Optional directory for exported demo JSON. Defaults to backend/.local_data/demo_cases/<case_id>/",
    )
    parser.add_argument(
        "--skip-kb-b-index",
        action="store_true",
        help="Do not auto-index claimmate_rag_docs when KB-B is empty.",
    )
    return parser.parse_args()


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

def _build_output_dir(case_id: str, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (DEMO_OUTPUT_ROOT / case_id).resolve()


async def main() -> None:
    args = parse_args()
    if not ai_config.database_url:
        raise SystemExit("DATABASE_URL is required before running scripts/seed_accident_demo.py.")

    output_dir = _build_output_dir(args.case_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        seeded = await seed_demo_accident_case(
            args.case_id,
            allow_index_kb_b=not args.skip_kb_b_index,
        )
    finally:
        await engine.dispose()

    _json_dump(output_dir / "request_stage_a.json", seeded["stage_a"])
    _json_dump(output_dir / "request_stage_b.json", seeded["stage_b"])
    _json_dump(output_dir / "request_claim_dates.json", seeded["claim_dates"])
    _json_dump(
        output_dir / "response_report.json",
        {
            "case_id": args.case_id,
            "report_payload": seeded["report_payload"],
            "chat_context": seeded["chat_context"],
        },
    )

    chat_events = seeded["sample_chat_requests"]
    chat_responses = seeded["sample_chat_responses"]
    for label, payload in chat_events.items():
        _json_dump(output_dir / f"request_chat_{label}.json", payload)
        if label in chat_responses:
            _json_dump(output_dir / f"response_chat_{label}.json", {"case_id": args.case_id, "response": chat_responses[label]})

    exported_files = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    if "summary.json" not in exported_files:
        exported_files.append("summary.json")

    summary = {
        "case_id": args.case_id,
        "output_dir": str(output_dir),
        "kb_b_status": seeded["kb_b_status"],
        "exported_files": exported_files,
        "chat_errors": seeded["sample_chat_errors"],
        "report_title": seeded["report_payload"]["report_title"],
        "chat_context_title": seeded["chat_context"]["pinned_document_title"],
    }
    _json_dump(output_dir / "summary.json", summary)

    print(f"Seeded accident demo case: {args.case_id}")
    print(f"KB-B status: {summary['kb_b_status']}")
    print(f"Output directory: {output_dir}")
    print("Generated files:")
    for name in summary["exported_files"]:
        print(f"- {name}")
    if summary["chat_errors"]:
        print("Chat generation warnings:")
        for label, err in summary["chat_errors"].items():
            print(f"- {label}: {err}")


if __name__ == "__main__":
    asyncio.run(main())

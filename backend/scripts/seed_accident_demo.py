from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from openai import OpenAIError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
DEMO_OUTPUT_ROOT = BACKEND_ROOT / ".local_data" / "demo_cases"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.chat.chat_ai_service import handle_chat_event
from ai.config import ai_config
from ai.ingestion.kb_b_loader import build_local_kb_b_sources, index_kb_b_sources
from ai.ingestion.vector_store import list_kb_b_chunks
from ai.runtime import bootstrap_vector_store, create_ai_engine
from app import case_service
from app.chat_serialize import ai_response_to_dict
from app.demo_seed_data import (
    DEMO_ACCIDENT_CASE_ID,
    build_demo_chat_event_payloads,
    build_demo_claim_dates_payload,
    build_demo_stage_a_payload,
    build_demo_stage_b_payload,
)
from models.ai_types import ChatEvent, ChatEventTrigger, Participant


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


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def _build_output_dir(case_id: str, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (DEMO_OUTPUT_ROOT / case_id).resolve()


async def _ensure_kb_b_ready(*, allow_index: bool) -> str:
    if await list_kb_b_chunks(limit=1):
        return "existing"
    if not allow_index:
        return "missing"
    docs_dir = REPO_ROOT / "claimmate_rag_docs"
    sources = build_local_kb_b_sources(docs_dir)
    if not sources:
        return "missing"
    await index_kb_b_sources(sources)
    return "indexed"


def _to_chat_event(payload: dict[str, Any]) -> ChatEvent:
    return ChatEvent(
        case_id=payload["case_id"],
        sender_role=payload["sender_role"],
        message_text=payload["message_text"],
        participants=[Participant(user_id=item["user_id"], role=item["role"]) for item in payload["participants"]],
        invite_sent=payload["invite_sent"],
        trigger=ChatEventTrigger(payload["trigger"]),
        metadata=payload.get("metadata", {}),
    )


async def main() -> None:
    args = parse_args()
    if not ai_config.database_url:
        raise SystemExit("DATABASE_URL is required before running scripts/seed_accident_demo.py.")

    output_dir = _build_output_dir(args.case_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    stage_a = build_demo_stage_a_payload()
    stage_b = build_demo_stage_b_payload()
    claim_dates = build_demo_claim_dates_payload()
    chat_events = build_demo_chat_event_payloads(args.case_id)

    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        kb_b_status = await _ensure_kb_b_ready(allow_index=not args.skip_kb_b_index)
        await case_service.ensure_case(args.case_id)
        await case_service.patch_stage_a(args.case_id, stage_a)
        await case_service.patch_stage_b(args.case_id, stage_b)
        await case_service.update_claim_dates(
            args.case_id,
            claim_notice_at=_parse_dt(claim_dates["claim_notice_at"]),
            proof_of_claim_at=_parse_dt(claim_dates["proof_of_claim_at"]),
        )
        report_payload, chat_context = await case_service.generate_and_store_report(args.case_id)

        chat_responses: dict[str, Any] = {}
        chat_errors: dict[str, str] = {}
        for label, payload in chat_events.items():
            try:
                response = await handle_chat_event(_to_chat_event(payload))
            except OpenAIError as exc:
                chat_errors[label] = str(exc)
                continue
            chat_responses[label] = None if response is None else ai_response_to_dict(response)
    finally:
        await engine.dispose()

    _json_dump(output_dir / "request_stage_a.json", stage_a)
    _json_dump(output_dir / "request_stage_b.json", stage_b)
    _json_dump(output_dir / "request_claim_dates.json", claim_dates)
    _json_dump(output_dir / "response_report.json", {"case_id": args.case_id, "report_payload": report_payload, "chat_context": chat_context})

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
        "kb_b_status": kb_b_status,
        "exported_files": exported_files,
        "chat_errors": chat_errors,
        "report_title": report_payload["report_title"],
        "chat_context_title": chat_context["pinned_document_title"],
    }
    _json_dump(output_dir / "summary.json", summary)

    print(f"Seeded accident demo case: {args.case_id}")
    print(f"KB-B status: {kb_b_status}")
    print(f"Output directory: {output_dir}")
    print("Generated files:")
    for name in summary["exported_files"]:
        print(f"- {name}")
    if chat_errors:
        print("Chat generation warnings:")
        for label, err in chat_errors.items():
            print(f"- {label}: {err}")


if __name__ == "__main__":
    asyncio.run(main())

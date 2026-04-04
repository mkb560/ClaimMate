from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEMO_OUTPUT_ROOT = BACKEND_ROOT / ".local_data" / "demo_policies"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.config import ai_config
from ai.runtime import bootstrap_vector_store, create_ai_engine
from app.demo_policy_service import list_demo_policy_keys, seed_demo_policy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed a fixed demo policy PDF into KB-A for a case.")
    parser.add_argument("--case-id", required=True, help="Case identifier to seed.")
    parser.add_argument(
        "--policy-key",
        help="Demo policy key to seed. Required unless case_id matches one of the fixed demo case ids.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory for exported summary JSON. Defaults to backend/.local_data/demo_policies/<case_id>/",
    )
    return parser.parse_args()


def _build_output_dir(case_id: str, explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    return (DEMO_OUTPUT_ROOT / case_id).resolve()


def _json_dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


async def main() -> None:
    args = parse_args()
    if not ai_config.database_url:
        raise SystemExit("DATABASE_URL is required before running scripts/seed_demo_policy.py.")

    output_dir = _build_output_dir(args.case_id, args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        seeded = await seed_demo_policy(args.case_id, args.policy_key)
    except KeyError as exc:
        available = ", ".join(list_demo_policy_keys())
        raise SystemExit(f"Unknown policy_key: {exc.args[0]}. Available policy keys: {available}") from exc
    except LookupError as exc:
        available = ", ".join(list_demo_policy_keys())
        raise SystemExit(
            "No default demo policy matches this case_id. "
            f"Provide --policy-key. Available policy keys: {available}"
        ) from exc
    finally:
        await engine.dispose()

    summary = {
        "case_id": seeded["case_id"],
        "policy_key": seeded["policy_key"],
        "default_case_id": seeded["default_case_id"],
        "label": seeded["label"],
        "filename": seeded["filename"],
        "chunk_count": seeded["chunk_count"],
        "sample_questions": seeded["sample_questions"],
        "output_dir": str(output_dir),
    }
    _json_dump(output_dir / "summary.json", summary)

    print(f"Seeded demo policy into case: {seeded['case_id']}")
    print(f"Policy key: {seeded['policy_key']}")
    print(f"Source file: {seeded['filename']}")
    print(f"Chunk count: {seeded['chunk_count']}")
    print(f"Output directory: {output_dir}")
    print("Sample questions:")
    for question in seeded["sample_questions"]:
        print(f"- {question}")


if __name__ == "__main__":
    asyncio.run(main())

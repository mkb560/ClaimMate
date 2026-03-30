from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.ingestion.ingest_policy import ingest_local_policy_file
from ai.runtime import bootstrap_vector_store, create_ai_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest a local policy PDF into KB-A.")
    parser.add_argument("pdf_path", help="Path to the local policy PDF.")
    parser.add_argument("--case-id", required=True, help="Case identifier to store chunks under.")
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    pdf_path = Path(args.pdf_path).expanduser().resolve()
    if not pdf_path.is_file():
        raise FileNotFoundError(f"Policy PDF not found: {pdf_path}")

    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        chunk_count = await ingest_local_policy_file(pdf_path, case_id=args.case_id)
    finally:
        await engine.dispose()

    print(f"Ingested {pdf_path} into case_id={args.case_id} with {chunk_count} chunk(s).")


if __name__ == "__main__":
    asyncio.run(main())

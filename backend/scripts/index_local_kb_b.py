from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.ingestion.kb_b_loader import build_local_kb_b_sources, index_kb_b_sources
from ai.runtime import bootstrap_vector_store, create_ai_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index local KB-B documents into pgvector.")
    parser.add_argument(
        "--docs-dir",
        default=str(REPO_ROOT / "claimmate_rag_docs"),
        help="Directory containing local regulatory/reference files.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    docs_dir = Path(args.docs_dir).expanduser().resolve()
    sources = build_local_kb_b_sources(docs_dir)
    if not sources:
        raise RuntimeError(f"No supported KB-B files found in {docs_dir}")

    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        results = await index_kb_b_sources(sources)
    finally:
        await engine.dispose()

    print(f"Indexed {len(results)} KB-B documents from {docs_dir}")
    total_chunks = 0
    for result in results:
        total_chunks += result.chunk_count
        print(
            f"- {result.source_label}: {result.page_count} page(s), "
            f"{result.chunk_count} chunk(s), document_id={result.document_id}"
        )
    print(f"Total chunks stored: {total_chunks}")


if __name__ == "__main__":
    asyncio.run(main())

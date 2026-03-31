from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from ai.ingestion.ingest_policy import ingest_local_policy_file
from ai.rag.query_engine import answer_policy_question
from ai.runtime import bootstrap_vector_store, create_ai_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the local RAG store.")
    parser.add_argument("question", help="User question to ask the RAG system.")
    parser.add_argument(
        "--case-id",
        default="demo-case",
        help="Case identifier for policy retrieval. Leave the default to query KB-B only.",
    )
    parser.add_argument(
        "--policy-pdf",
        help="Optional local policy PDF to ingest into KB-A before querying.",
    )
    parser.add_argument(
        "--skip-policy-reindex",
        action="store_true",
        help="If --policy-pdf is provided, skip re-ingesting it before the query.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    engine = create_ai_engine()
    try:
        await bootstrap_vector_store(engine)
        if args.policy_pdf and not args.skip_policy_reindex:
            policy_path = Path(args.policy_pdf).expanduser().resolve()
            if not policy_path.is_file():
                raise FileNotFoundError(f"Policy PDF not found: {policy_path}")
            chunk_count = await ingest_local_policy_file(policy_path, case_id=args.case_id)
            print(f"Ingested {policy_path.name} into case_id={args.case_id} with {chunk_count} chunk(s).\n")
        answer = await answer_policy_question(args.case_id, args.question)
    finally:
        await engine.dispose()

    print(answer.answer)
    if answer.citations:
        print("\nCitations:")
        for citation in answer.citations:
            location_parts: list[str] = []
            if citation.page_num is not None:
                location_parts.append(f"page {citation.page_num}")
            if citation.section:
                location_parts.append(f"section {citation.section}")
            location = ", ".join(location_parts) if location_parts else "no page metadata"
            print(f"- {citation.source_label} ({location})")


if __name__ == "__main__":
    asyncio.run(main())

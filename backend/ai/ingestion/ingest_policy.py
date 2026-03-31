from __future__ import annotations

import asyncio
from pathlib import Path

import boto3

from ai.config import ai_config
from ai.ingestion.chunker import chunk_policy_pages
from ai.ingestion.embedder import embed_texts
from ai.ingestion.pdf_parser import parse_pdf_bytes
from ai.ingestion.types import EmbeddedChunk
from ai.ingestion.vector_store import replace_case_chunks


def _s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=ai_config.aws_access_key_id,
        aws_secret_access_key=ai_config.aws_secret_access_key,
        region_name=ai_config.aws_region,
    )


def _fetch_policy_bytes(s3_key: str) -> bytes:
    if not ai_config.s3_bucket_name:
        raise RuntimeError("S3_BUCKET_NAME is required to ingest policy PDFs from object storage.")
    response = _s3_client().get_object(Bucket=ai_config.s3_bucket_name, Key=s3_key)
    return response["Body"].read()


def _read_policy_file(pdf_path: str | Path) -> bytes:
    return Path(pdf_path).expanduser().resolve().read_bytes()


def _policy_source_label(pdf_path: str | Path | None) -> str:
    if pdf_path is None:
        return "Your Policy"
    path = Path(pdf_path)
    return f"Your Policy ({path.name})"


async def _index_policy_bytes(policy_bytes: bytes, case_id: str, *, pdf_path: str | Path | None = None) -> int:
    pages = await asyncio.to_thread(parse_pdf_bytes, policy_bytes)
    chunks = chunk_policy_pages(pages, case_id=case_id)
    embeddings = await embed_texts([chunk.chunk_text for chunk in chunks])
    source_label = _policy_source_label(pdf_path)
    resolved_path = str(Path(pdf_path).expanduser().resolve()) if pdf_path is not None else None

    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        embedded_chunks.append(
            EmbeddedChunk(
                source_type=chunk.source_type,
                case_id=case_id,
                document_id=chunk.document_id,
                chunk_text=chunk.chunk_text,
                embedding=embedding,
                page_num=chunk.page_num,
                section=chunk.section,
                metadata={
                    **chunk.metadata,
                    "source_label": source_label,
                    "policy_path": resolved_path,
                },
            )
        )

    await replace_case_chunks(case_id, embedded_chunks)
    return len(embedded_chunks)


async def ingest_policy(s3_key: str, case_id: str) -> int:
    policy_bytes = await asyncio.to_thread(_fetch_policy_bytes, s3_key)
    return await _index_policy_bytes(policy_bytes, case_id)


async def ingest_local_policy_file(pdf_path: str | Path, case_id: str) -> int:
    policy_bytes = await asyncio.to_thread(_read_policy_file, pdf_path)
    return await _index_policy_bytes(policy_bytes, case_id, pdf_path=pdf_path)

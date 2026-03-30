from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import boto3
import requests

from ai.config import ai_config
from ai.ingestion.kb_b_catalog import source_label_for_document
from ai.ingestion.chunker import chunk_regulatory_pages
from ai.ingestion.embedder import embed_texts
from ai.ingestion.html_parser import parse_html_bytes
from ai.ingestion.pdf_parser import parse_pdf_bytes
from ai.ingestion.types import EmbeddedChunk
from ai.ingestion.vector_store import replace_kb_b_document


@dataclass(frozen=True, slots=True)
class KBBSource:
    document_id: str
    location: str
    filename: str | None = None
    source_label: str | None = None


@dataclass(frozen=True, slots=True)
class KBBIndexResult:
    document_id: str
    source_label: str
    location: str
    page_count: int
    chunk_count: int


KB_B_SOURCES: tuple[KBBSource, ...] = (
    KBBSource(
        document_id="iso_pp_0001",
        location="https://doi.nv.gov/uploadedFiles/doinvgov/_public-documents/Consumers/PP_00_01_06_98.pdf",
        filename="kb-b/iso_pp_0001.pdf",
        source_label=source_label_for_document("iso_pp_0001"),
    ),
    KBBSource(
        document_id="naic_model_900",
        location="https://content.naic.org/sites/default/files/model-law-900.pdf",
        filename="kb-b/naic_model_900.pdf",
        source_label=source_label_for_document("naic_model_900"),
    ),
    KBBSource(
        document_id="naic_model_902",
        location="https://content.naic.org/sites/default/files/model-law-902.pdf",
        filename="kb-b/naic_model_902.pdf",
        source_label=source_label_for_document("naic_model_902"),
    ),
    KBBSource(
        document_id="ca_fair_claims",
        location="https://www.insurance.ca.gov/01-consumers/130-laws-regs-hearings/05-CCR/fair-claims-regs.cfm",
        filename="kb-b/ca_fair_claims.html",
        source_label=source_label_for_document("ca_fair_claims"),
    ),
    KBBSource(
        document_id="iii_nofault",
        location="https://www.iii.org/article/background-on-no-fault-auto-insurance",
        filename="kb-b/iii_nofault.html",
        source_label=source_label_for_document("iii_nofault"),
    ),
    KBBSource(
        document_id="naic_complaints",
        location="https://content.naic.org/cis_agg_reason.htm",
        filename="kb-b/naic_complaints.html",
        source_label=source_label_for_document("naic_complaints"),
    ),
)

SUPPORTED_LOCAL_EXTENSIONS = {".pdf", ".html", ".htm"}


def _s3_client():
    if not ai_config.s3_bucket_name:
        return None
    return boto3.client(
        "s3",
        aws_access_key_id=ai_config.aws_access_key_id,
        aws_secret_access_key=ai_config.aws_secret_access_key,
        region_name=ai_config.aws_region,
    )


def _is_remote_location(location: str) -> bool:
    return location.startswith("http://") or location.startswith("https://")


def _load_source_bytes(source: KBBSource) -> bytes:
    if _is_remote_location(source.location):
        response = requests.get(source.location, timeout=30)
        response.raise_for_status()
        return response.content
    return Path(source.location).read_bytes()


def _upload_backup(source: KBBSource, content: bytes) -> None:
    s3 = _s3_client()
    if s3 is None or not source.filename:
        return
    s3.put_object(Bucket=ai_config.s3_bucket_name, Key=source.filename, Body=content)


def build_local_kb_b_sources(root_dir: str | Path) -> tuple[KBBSource, ...]:
    root_path = Path(root_dir).expanduser().resolve()
    if not root_path.is_dir():
        raise FileNotFoundError(f"KB-B directory not found: {root_path}")

    sources: list[KBBSource] = []
    for path in sorted(root_path.rglob("*")):
        if not path.is_file():
            continue
        if path.name.startswith(".") or path.suffix.lower() not in SUPPORTED_LOCAL_EXTENSIONS:
            continue

        document_id = path.stem.lower()
        sources.append(
            KBBSource(
                document_id=document_id,
                location=str(path),
                source_label=source_label_for_document(document_id),
            )
        )

    return tuple(sources)


async def _load_source(source: KBBSource) -> KBBIndexResult:
    raw_bytes = await asyncio.to_thread(_load_source_bytes, source)
    await asyncio.to_thread(_upload_backup, source, raw_bytes)

    if source.location.lower().endswith(".pdf"):
        pages = await asyncio.to_thread(parse_pdf_bytes, raw_bytes)
    else:
        pages = await asyncio.to_thread(parse_html_bytes, raw_bytes)

    chunks = chunk_regulatory_pages(pages, source.document_id)
    embeddings = await embed_texts([chunk.chunk_text for chunk in chunks])
    embedded_chunks: list[EmbeddedChunk] = []
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        embedded_chunks.append(
            EmbeddedChunk(
                source_type=chunk.source_type,
                case_id=None,
                document_id=chunk.document_id,
                chunk_text=chunk.chunk_text,
                embedding=embedding,
                page_num=chunk.page_num,
                section=chunk.section,
                metadata={
                    **chunk.metadata,
                    "source_label": source.source_label or source_label_for_document(source.document_id),
                },
            )
        )
    await replace_kb_b_document(source.document_id, embedded_chunks)
    return KBBIndexResult(
        document_id=source.document_id,
        source_label=source.source_label or source_label_for_document(source.document_id) or source.document_id,
        location=source.location,
        page_count=len(pages),
        chunk_count=len(embedded_chunks),
    )


async def index_kb_b_sources(sources: Sequence[KBBSource] = KB_B_SOURCES) -> list[KBBIndexResult]:
    results: list[KBBIndexResult] = []
    for source in sources:
        results.append(await _load_source(source))
    return results

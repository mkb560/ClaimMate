from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Sequence

import boto3
import requests

from ai.config import ai_config
from ai.ingestion.chunker import chunk_regulatory_pages
from ai.ingestion.embedder import embed_texts
from ai.ingestion.html_parser import parse_html_bytes
from ai.ingestion.pdf_parser import parse_pdf_bytes
from ai.ingestion.types import EmbeddedChunk
from ai.ingestion.vector_store import replace_kb_b_document


@dataclass(frozen=True, slots=True)
class KBBSource:
    document_id: str
    url: str
    filename: str


KB_B_SOURCES: tuple[KBBSource, ...] = (
    KBBSource(
        document_id="iso_pp_0001",
        url="https://doi.nv.gov/uploadedFiles/doinvgov/_public-documents/Consumers/PP_00_01_06_98.pdf",
        filename="kb-b/iso_pp_0001.pdf",
    ),
    KBBSource(
        document_id="naic_model_900",
        url="https://content.naic.org/sites/default/files/model-law-900.pdf",
        filename="kb-b/naic_model_900.pdf",
    ),
    KBBSource(
        document_id="naic_model_902",
        url="https://content.naic.org/sites/default/files/model-law-902.pdf",
        filename="kb-b/naic_model_902.pdf",
    ),
    KBBSource(
        document_id="ca_fair_claims",
        url="https://www.insurance.ca.gov/01-consumers/130-laws-regs-hearings/05-CCR/fair-claims-regs.cfm",
        filename="kb-b/ca_fair_claims.html",
    ),
    KBBSource(
        document_id="iii_nofault",
        url="https://www.iii.org/article/background-on-no-fault-auto-insurance",
        filename="kb-b/iii_nofault.html",
    ),
    KBBSource(
        document_id="naic_complaints",
        url="https://content.naic.org/cis_agg_reason.htm",
        filename="kb-b/naic_complaints.html",
    ),
)


def _s3_client():
    if not ai_config.s3_bucket_name:
        return None
    return boto3.client(
        "s3",
        aws_access_key_id=ai_config.aws_access_key_id,
        aws_secret_access_key=ai_config.aws_secret_access_key,
        region_name=ai_config.aws_region,
    )


def _download_bytes(url: str) -> bytes:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.content


def _upload_backup(source: KBBSource, content: bytes) -> None:
    s3 = _s3_client()
    if s3 is None:
        return
    s3.put_object(Bucket=ai_config.s3_bucket_name, Key=source.filename, Body=content)


async def _load_source(source: KBBSource) -> None:
    raw_bytes = await asyncio.to_thread(_download_bytes, source.url)
    await asyncio.to_thread(_upload_backup, source, raw_bytes)

    if source.url.endswith(".pdf"):
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
                metadata=chunk.metadata,
            )
        )
    await replace_kb_b_document(source.document_id, embedded_chunks)


async def index_kb_b_sources(sources: Sequence[KBBSource] = KB_B_SOURCES) -> None:
    for source in sources:
        await _load_source(source)


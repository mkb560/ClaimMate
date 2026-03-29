from __future__ import annotations

import re
from functools import lru_cache

import tiktoken

from ai.config import ai_config
from ai.ingestion.types import ChunkPayload, ParsedPage, SourceType

STATUTE_RE = re.compile(r"(§\s*\d{4,}\.\d+[a-z]?(?:\([a-z0-9]+\))?)", re.IGNORECASE)
HEADING_RE = re.compile(r"^[A-Z][A-Z0-9 /,&\-]{3,}$")


@lru_cache(maxsize=1)
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str) -> int:
    return len(_encoding().encode(text))


def _detect_section(text: str) -> str | None:
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        statute_match = STATUTE_RE.search(line)
        if statute_match:
            return statute_match.group(1).replace("  ", " ")
        if HEADING_RE.match(line):
            return line[:256]
    return None


def _slice_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    tokens = _encoding().encode(text)
    if not tokens:
        return []

    step = max(chunk_size - overlap, 1)
    chunks: list[str] = []
    for start in range(0, len(tokens), step):
        chunk = _encoding().decode(tokens[start : start + chunk_size]).strip()
        if chunk:
            chunks.append(chunk)
        if start + chunk_size >= len(tokens):
            break
    return chunks


def _chunk_pages(
    pages: list[ParsedPage],
    *,
    source_type: SourceType,
    chunk_size: int,
    overlap: int,
    case_id: str | None = None,
    document_id: str | None = None,
) -> list[ChunkPayload]:
    chunks: list[ChunkPayload] = []
    for page in pages:
        page_text = page.text.strip()
        if not page_text:
            continue

        section = page.section or _detect_section(page_text)
        for chunk_text in _slice_text(page_text, chunk_size=chunk_size, overlap=overlap):
            metadata = dict(page.metadata)
            if section:
                metadata.setdefault("section", section)
            chunks.append(
                ChunkPayload(
                    source_type=source_type,
                    chunk_text=chunk_text,
                    page_num=page.page_num,
                    section=section,
                    case_id=case_id,
                    document_id=document_id,
                    metadata=metadata,
                )
            )
    return chunks


def chunk_policy_pages(pages: list[ParsedPage], case_id: str) -> list[ChunkPayload]:
    return _chunk_pages(
        pages,
        source_type=SourceType.KB_A,
        chunk_size=ai_config.kb_a_chunk_size,
        overlap=ai_config.kb_a_chunk_overlap,
        case_id=case_id,
        document_id="policy_pdf",
    )


def chunk_regulatory_pages(pages: list[ParsedPage], document_id: str) -> list[ChunkPayload]:
    return _chunk_pages(
        pages,
        source_type=SourceType.KB_B,
        chunk_size=ai_config.kb_b_chunk_size,
        overlap=ai_config.kb_b_chunk_overlap,
        document_id=document_id,
    )


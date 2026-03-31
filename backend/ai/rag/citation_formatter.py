from __future__ import annotations

import re
from typing import Sequence

from ai.ingestion.kb_b_catalog import source_label_for_document
from ai.ingestion.vector_store import RetrievedChunk
from models.ai_types import Citation

SOURCE_REF_RE = re.compile(r"\[S(\d+)\]")


def normalize_citation_section(section: str | None) -> str | None:
    if section is None:
        return None

    cleaned = section.strip()
    if not cleaned:
        return None

    letters_only = re.sub(r"[^A-Za-z]", "", cleaned)
    unique_letters = set(letters_only.upper())
    if (
        len(cleaned) >= 24
        and " " not in cleaned
        and not cleaned.startswith("§")
        and letters_only
        and len(unique_letters) <= 6
    ):
        return None

    return cleaned


def source_label_for_chunk(chunk: RetrievedChunk) -> str:
    metadata_label = chunk.metadata.get("source_label") or chunk.metadata.get("title")
    if isinstance(metadata_label, str) and metadata_label.strip():
        return metadata_label.strip()

    if label := source_label_for_document(chunk.document_id):
        return label

    return "Your Policy" if chunk.source_type == "kb_a" else "Regulatory Source"


def build_context_sections(
    policy_chunks: Sequence[RetrievedChunk],
    regulatory_chunks: Sequence[RetrievedChunk],
) -> tuple[str, dict[str, RetrievedChunk]]:
    source_index: dict[str, RetrievedChunk] = {}
    context_parts: list[str] = []
    counter = 1

    for block_name, chunks in (
        ("policy_context", policy_chunks),
        ("regulatory_context", regulatory_chunks),
    ):
        lines: list[str] = []
        for chunk in chunks:
            ref = f"S{counter}"
            source_index[ref] = chunk
            label = source_label_for_chunk(chunk)
            location: list[str] = []
            if chunk.page_num is not None:
                location.append(f"Page {chunk.page_num}")
            if display_section := normalize_citation_section(chunk.section):
                location.append(f"Section {display_section}")
            location_text = " | ".join(location) if location else "No page metadata"
            lines.append(f"[{ref}] {label} | {location_text}\n{chunk.chunk_text}")
            counter += 1

        joined_lines = "\n\n".join(lines) if lines else "No context available."
        context_parts.append(f"<{block_name}>\n{joined_lines}\n</{block_name}>")

    return "\n\n".join(context_parts), source_index


def citations_from_answer(answer: str, source_index: dict[str, RetrievedChunk]) -> list[Citation]:
    refs = SOURCE_REF_RE.findall(answer)
    seen: set[str] = set()
    citations: list[Citation] = []

    for ref_num in refs:
        ref = f"S{ref_num}"
        if ref in seen or ref not in source_index:
            continue
        seen.add(ref)
        chunk = source_index[ref]
        citations.append(
            Citation(
                source_type=chunk.source_type,
                source_label=source_label_for_chunk(chunk),
                document_id=chunk.document_id or ("policy_pdf" if chunk.source_type == "kb_a" else "unknown"),
                page_num=chunk.page_num,
                section=normalize_citation_section(chunk.section),
                excerpt=chunk.chunk_text[:100].strip(),
            )
        )

    return citations


def fallback_citations(chunks: Sequence[RetrievedChunk], limit: int = 4) -> list[Citation]:
    citations: list[Citation] = []
    seen: set[tuple[str, int | None, str | None]] = set()
    for chunk in chunks:
        key = (chunk.document_id or chunk.source_type, chunk.page_num, chunk.section)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            Citation(
                source_type=chunk.source_type,
                source_label=source_label_for_chunk(chunk),
                document_id=chunk.document_id or ("policy_pdf" if chunk.source_type == "kb_a" else "unknown"),
                page_num=chunk.page_num,
                section=normalize_citation_section(chunk.section),
                excerpt=chunk.chunk_text[:100].strip(),
            )
        )
        if len(citations) >= limit:
            break
    return citations

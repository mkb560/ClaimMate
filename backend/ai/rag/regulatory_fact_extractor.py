from __future__ import annotations

import re
from typing import Sequence

from ai.ingestion.vector_store import RetrievedChunk
from ai.rag.citation_formatter import normalize_citation_section, source_label_for_chunk
from models.ai_types import AnswerResponse, Citation

CLAIM_ACK_RULE_DOCUMENT_ID = "ca_reg_2695_5_duties_upon_receipt_of_communications"

NOTICE_OF_CLAIM_RE = re.compile(r"upon receiving notice of claim", re.IGNORECASE)
FIFTEEN_DAY_RE = re.compile(r"fifteen\s*\(15\)\s*calendar days|15\s+calendar days", re.IGNORECASE)
ACKNOWLEDGMENT_RE = re.compile(r"acknowledge receipt of such notice", re.IGNORECASE)
INVESTIGATION_RE = re.compile(r"begin any necessary investigation", re.IGNORECASE)


def is_structured_regulatory_question(question: str) -> bool:
    lowered = question.lower()
    mentions_15_day_window = "15" in lowered or "fifteen" in lowered
    mentions_claim_context = "claim" in lowered or "notice of claim" in lowered
    mentions_acknowledgment = "acknowledg" in lowered or "insurer do" in lowered or "receiving notice of claim" in lowered
    return mentions_15_day_window and mentions_claim_context and mentions_acknowledgment


def _citation_for_chunk(chunk: RetrievedChunk) -> Citation:
    return Citation(
        source_type="kb_b",
        source_label=source_label_for_chunk(chunk),
        document_id=chunk.document_id or "unknown",
        page_num=chunk.page_num,
        section=normalize_citation_section(chunk.section),
        excerpt=" ".join(chunk.chunk_text.split())[:160],
    )


def answer_structured_regulatory_question(question: str, chunks: Sequence[RetrievedChunk]) -> AnswerResponse | None:
    if not is_structured_regulatory_question(question):
        return None

    acknowledgment_chunk: RetrievedChunk | None = None
    investigation_chunk: RetrievedChunk | None = None

    for chunk in chunks:
        lowered = chunk.chunk_text.lower()
        if (
            acknowledgment_chunk is None
            and NOTICE_OF_CLAIM_RE.search(lowered)
            and FIFTEEN_DAY_RE.search(lowered)
            and ACKNOWLEDGMENT_RE.search(lowered)
        ):
            acknowledgment_chunk = chunk
        if investigation_chunk is None and INVESTIGATION_RE.search(lowered):
            investigation_chunk = chunk

    if acknowledgment_chunk is None or investigation_chunk is None:
        return None

    citations: list[Citation] = []
    ref_map: dict[tuple[str | None, int | None, str | None], str] = {}

    def ref_for(chunk: RetrievedChunk) -> str:
        key = (chunk.document_id, chunk.page_num, chunk.section)
        if key not in ref_map:
            ref_map[key] = f"S{len(ref_map) + 1}"
            citations.append(_citation_for_chunk(chunk))
        return ref_map[key]

    acknowledgment_ref = ref_for(acknowledgment_chunk)
    investigation_ref = ref_for(investigation_chunk)
    citation_refs = f"[{acknowledgment_ref}]" if acknowledgment_ref == investigation_ref else f"[{acknowledgment_ref}][{investigation_ref}]"
    answer = (
        "California's 15-day claim rule says that after receiving notice of claim, "
        "the insurer must acknowledge receipt of the notice and begin any necessary investigation "
        "within 15 calendar days, unless the notice is a notice of legal action. "
        f"{citation_refs}"
    )
    return AnswerResponse(
        answer=answer,
        citations=citations,
        disclaimer="",
    )

from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from ai.clients import get_openai_client
from ai.config import ai_config
from ai.ingestion.embedder import embed_texts
from ai.ingestion.kb_b_catalog import DISPUTE_RELEVANT_DOCUMENT_IDS
from ai.ingestion.vector_store import list_policy_chunks, search_case_chunks, search_kb_b_chunks
from ai.policy.fact_extractor import answer_structured_policy_question
from ai.rag.citation_formatter import build_context_sections, citations_from_answer, fallback_citations, source_label_for_chunk
from ai.rag.prompt_templates import DISCLAIMER_FOOTER, NOT_ENOUGH_INFO_MESSAGE, SYSTEM_PROMPT_DISPUTE, SYSTEM_PROMPT_RAG, SYSTEM_PROMPT_RESCUE, compose_system_prompt
from models.ai_types import AnswerResponse, ChatStage


def _normalize_answer(answer: str) -> str:
    stripped = answer.strip()
    if DISCLAIMER_FOOTER in stripped:
        stripped = stripped.replace(DISCLAIMER_FOOTER, "").strip()
    return f"{stripped}\n\n{DISCLAIMER_FOOTER}"


def _is_not_enough_info(answer: str) -> bool:
    return NOT_ENOUGH_INFO_MESSAGE.lower() in answer.lower()


def _build_rescue_context(source_index: dict[str, object], *, limit: int = 4) -> str:
    lines: list[str] = []
    for ref, chunk in list(source_index.items())[:limit]:
        label = source_label_for_chunk(chunk)
        location: list[str] = []
        if chunk.page_num is not None:
            location.append(f"Page {chunk.page_num}")
        if chunk.section:
            location.append(f"Section {chunk.section}")
        location_text = " | ".join(location) if location else "No page metadata"
        lines.append(f"[{ref}] {label} | {location_text}\n{chunk.chunk_text}")
    return "<snippets>\n" + "\n\n".join(lines) + "\n</snippets>"


async def _generate_rescue_answer(
    *,
    question: str,
    source_index: dict[str, object],
    client: AsyncOpenAI,
) -> str:
    response = await client.chat.completions.create(
        model=ai_config.rag_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_RESCUE},
            {
                "role": "user",
                "content": (
                    f"{_build_rescue_context(source_index)}\n\n"
                    f"Question: {question}\n\n"
                    "Answer with inline citations after each factual sentence."
                ),
            },
        ],
        max_completion_tokens=700,
    )
    return response.choices[0].message.content or NOT_ENOUGH_INFO_MESSAGE


async def _embed_query(question: str) -> list[float]:
    return (await embed_texts([question]))[0]


async def _generate_answer(
    *,
    question: str,
    policy_chunks,
    regulatory_chunks,
    client: AsyncOpenAI | None,
    system_prompt: str,
) -> AnswerResponse:
    all_chunks = [*policy_chunks, *regulatory_chunks]
    if not all_chunks:
        return AnswerResponse(
            answer=f"{NOT_ENOUGH_INFO_MESSAGE}\n\n{DISCLAIMER_FOOTER}",
            citations=[],
            disclaimer=DISCLAIMER_FOOTER,
        )

    context_text, source_index = build_context_sections(policy_chunks, regulatory_chunks)
    openai_client = client or get_openai_client()
    response = await openai_client.chat.completions.create(
        model=ai_config.rag_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    f"{context_text}\n\nQuestion: {question}\n\n"
                    "Answer the question with inline [S#] citations after every factual sentence."
                ),
            },
        ],
        max_completion_tokens=1400,
    )
    raw_answer = response.choices[0].message.content or NOT_ENOUGH_INFO_MESSAGE
    if _is_not_enough_info(raw_answer):
        rescued_answer = await _generate_rescue_answer(
            question=question,
            source_index=source_index,
            client=openai_client,
        )
        if not _is_not_enough_info(rescued_answer):
            raw_answer = rescued_answer
    citations = citations_from_answer(raw_answer, source_index) or fallback_citations(all_chunks)
    return AnswerResponse(
        answer=_normalize_answer(raw_answer),
        citations=citations,
        disclaimer=DISCLAIMER_FOOTER,
    )


async def answer_policy_question(case_id: str, question: str, *, client: AsyncOpenAI | None = None) -> AnswerResponse:
    query_embedding = await _embed_query(question)
    policy_chunks, regulatory_chunks = await asyncio.gather(
        search_case_chunks(case_id, query_embedding, top_k=ai_config.rag_top_k_per_source),
        search_kb_b_chunks(query_embedding, top_k=ai_config.rag_top_k_per_source),
    )
    if policy_chunks:
        all_policy_chunks = await list_policy_chunks(case_id, limit=None)
        if structured_answer := answer_structured_policy_question(question, all_policy_chunks):
            structured_answer.answer = _normalize_answer(structured_answer.answer)
            structured_answer.disclaimer = DISCLAIMER_FOOTER
            return structured_answer
    return await _generate_answer(
        question=question,
        policy_chunks=policy_chunks,
        regulatory_chunks=regulatory_chunks,
        client=client,
        system_prompt=SYSTEM_PROMPT_RAG,
    )


async def answer_dispute_question(
    case_id: str,
    question: str,
    *,
    client: AsyncOpenAI | None = None,
    stage_instruction: str | None = None,
) -> AnswerResponse:
    query_embedding = await _embed_query(question)
    policy_chunks, regulatory_chunks = await asyncio.gather(
        search_case_chunks(case_id, query_embedding, top_k=ai_config.rag_top_k_per_source),
        search_kb_b_chunks(
            query_embedding,
            top_k=ai_config.rag_top_k_per_source,
            document_ids=DISPUTE_RELEVANT_DOCUMENT_IDS,
        ),
    )
    return await _generate_answer(
        question=question,
        policy_chunks=policy_chunks,
        regulatory_chunks=regulatory_chunks,
        client=client,
        system_prompt=compose_system_prompt(base_prompt=SYSTEM_PROMPT_DISPUTE, stage_instruction=stage_instruction),
    )


async def summarize_policy_highlights(case_id: str, stage: ChatStage) -> AnswerResponse:
    chunks = await list_policy_chunks(case_id, limit=3)
    citations = fallback_citations(chunks, limit=3)
    sections = [citation.section for citation in citations if citation.section]
    unique_sections: list[str] = []
    for section in sections:
        if section not in unique_sections:
            unique_sections.append(section)

    if unique_sections:
        highlights = ", ".join(unique_sections[:3])
        body = (
            "Your policy is indexed and ready for questions. "
            f"Useful sections to ask about include {highlights}. "
            "Try asking @AI about deductibles, rental reimbursement, exclusions, or claim steps."
        )
    else:
        body = (
            "Your policy is indexed and ready for questions. "
            "Ask @AI about deductibles, coverage limits, rental reimbursement, exclusions, or claim steps."
        )

    if stage == ChatStage.STAGE_3:
        body = f"For reference: {body}"

    return AnswerResponse(
        answer=f"{body}\n\n{DISCLAIMER_FOOTER}",
        citations=citations,
        disclaimer=DISCLAIMER_FOOTER,
    )

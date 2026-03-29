from __future__ import annotations

import asyncio

from openai import AsyncOpenAI

from ai.clients import get_openai_client
from ai.config import ai_config
from ai.ingestion.embedder import embed_texts
from ai.ingestion.vector_store import list_policy_chunks, search_case_chunks, search_kb_b_chunks
from ai.rag.citation_formatter import build_context_sections, citations_from_answer, fallback_citations
from ai.rag.prompt_templates import DISCLAIMER_FOOTER, NOT_ENOUGH_INFO_MESSAGE, SYSTEM_PROMPT_DISPUTE, SYSTEM_PROMPT_RAG, compose_system_prompt
from models.ai_types import AnswerResponse, ChatStage


def _normalize_answer(answer: str) -> str:
    stripped = answer.strip()
    if DISCLAIMER_FOOTER in stripped:
        stripped = stripped.replace(DISCLAIMER_FOOTER, "").strip()
    return f"{stripped}\n\n{DISCLAIMER_FOOTER}"


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
        max_tokens=700,
    )
    raw_answer = response.choices[0].message.content or NOT_ENOUGH_INFO_MESSAGE
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
            document_ids=["ca_fair_claims", "naic_model_900", "naic_model_902"],
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

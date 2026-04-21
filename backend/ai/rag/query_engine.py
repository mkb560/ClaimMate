from __future__ import annotations

import asyncio
import re
from typing import Any, Sequence

from openai import AsyncOpenAI

from ai.clients import get_openai_client
from ai.config import ai_config
from ai.ingestion.embedder import embed_texts
from ai.ingestion.kb_b_catalog import DISPUTE_RELEVANT_DOCUMENT_IDS
from ai.ingestion.vector_store import RetrievedChunk, list_kb_b_chunks, list_policy_chunks, search_case_chunks, search_kb_b_chunks
from ai.policy.fact_extractor import (
    PolicyFact,
    answer_structured_policy_question,
    extract_policy_facts,
    is_structured_policy_fact_question,
)
from ai.rag.regulatory_fact_extractor import CLAIM_ACK_RULE_DOCUMENT_ID, answer_structured_regulatory_question, is_structured_regulatory_question
from ai.rag.citation_formatter import (
    build_context_sections,
    citations_from_answer,
    fallback_citations,
    normalize_citation_section,
    source_label_for_chunk,
)
from ai.rag.prompt_templates import DISCLAIMER_FOOTER, NOT_ENOUGH_INFO_MESSAGE, SYSTEM_PROMPT_DISPUTE, SYSTEM_PROMPT_RAG, SYSTEM_PROMPT_RESCUE, compose_system_prompt
from models.ai_types import AnswerResponse, ChatStage, Citation


SUMMARY_WORDS = ("summarize", "summary", "overview", "bullet", "key point", "key points")
POLICY_SUMMARY_SUBJECTS = ("policy", "coverage", "coverages", "insurance", "document")
ACCIDENT_CONTEXT_WORDS = ("accident", "crash", "collision", "incident", "damage", "rear-end", "rear ended")
COVERAGE_CHECK_WORDS = ("coverage", "cover", "covered", "check", "look at", "look for", "policy")
NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}


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


def is_policy_summary_question(question: str) -> bool:
    lowered = question.lower()
    return any(word in lowered for word in SUMMARY_WORDS) and any(
        subject in lowered for subject in POLICY_SUMMARY_SUBJECTS
    )


def is_accident_coverage_check_question(question: str) -> bool:
    lowered = question.lower()
    return any(word in lowered for word in ACCIDENT_CONTEXT_WORDS) and any(
        word in lowered for word in COVERAGE_CHECK_WORDS
    )


def _requested_bullet_count(question: str, *, default: int = 3) -> int:
    lowered = question.lower()
    if match := re.search(r"\b([1-5])\b", lowered):
        return max(1, min(5, int(match.group(1))))
    for word, value in NUMBER_WORDS.items():
        if re.search(rf"\b{word}\b", lowered):
            return value
    return default


def _first_fact(facts: dict[str, list[PolicyFact]], key: str) -> PolicyFact | None:
    values = facts.get(key) or []
    return values[0] if values else None


def _with_indefinite_article(text: str) -> str:
    article = "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {text}"


def _fact_citation(fact: PolicyFact) -> Citation:
    return Citation(
        source_type="kb_a",
        source_label=fact.source_label,
        document_id="policy_pdf",
        page_num=fact.page_num,
        section=normalize_citation_section(fact.section),
        excerpt=fact.excerpt,
    )


def _chunk_citation(chunk: RetrievedChunk) -> Citation:
    excerpt = chunk.chunk_text[:160].strip()
    if chunk.source_type == "case_context":
        excerpt = _compact_case_context_excerpt(chunk.chunk_text)
    return Citation(
        source_type=chunk.source_type,
        source_label=source_label_for_chunk(chunk),
        document_id=chunk.document_id or ("policy_pdf" if chunk.source_type == "kb_a" else "unknown"),
        page_num=chunk.page_num,
        section=normalize_citation_section(chunk.section),
        excerpt=excerpt,
    )


def _build_summary_answer(question: str, chunks: Sequence[RetrievedChunk]) -> AnswerResponse | None:
    if not chunks:
        return None

    facts = extract_policy_facts(chunks)
    citations: list[Citation] = []
    fact_refs: dict[tuple[str, str, int | None, str | None], str] = {}

    def ref_for(fact: PolicyFact) -> str:
        key = (fact.key, fact.value, fact.page_num, fact.section)
        if key not in fact_refs:
            fact_refs[key] = f"S{len(citations) + 1}"
            citations.append(_fact_citation(fact))
        return fact_refs[key]

    document_type = _first_fact(facts, "document_type")
    policyholders = _first_fact(facts, "policyholders")
    policy_number = _first_fact(facts, "policy_number")
    policy_period = _first_fact(facts, "policy_period")
    insurer = _first_fact(facts, "insurer")

    points: list[str] = []
    identity_bits: list[str] = []
    identity_refs: list[str] = []
    if document_type:
        identity_bits.append(f"this document looks like {_with_indefinite_article(document_type.value)}")
        identity_refs.append(ref_for(document_type))
    if policyholders:
        identity_bits.append(f"it lists {policyholders.value} as the policyholder(s)")
        identity_refs.append(ref_for(policyholders))
    if policy_number:
        identity_bits.append(f"the policy number is {policy_number.value}")
        identity_refs.append(ref_for(policy_number))
    if policy_period:
        identity_bits.append(f"the policy period is {policy_period.value}")
        identity_refs.append(ref_for(policy_period))
    if insurer:
        identity_bits.append(f"the insurer shown is {insurer.value}")
        identity_refs.append(ref_for(insurer))
    if identity_bits:
        points.append(f"Policy identity: {'; '.join(identity_bits)}. {''.join(f'[{ref}]' for ref in identity_refs)}")

    vehicle = _first_fact(facts, "vehicle_description")
    vin = _first_fact(facts, "vehicle_vin")
    liability = _first_fact(facts, "liability_limits")
    collision = _first_fact(facts, "collision_coverage")
    comprehensive = _first_fact(facts, "comprehensive_coverage")
    rental = _first_fact(facts, "rental_reimbursement")

    coverage_bits: list[str] = []
    coverage_refs: list[str] = []
    if vehicle:
        coverage_bits.append(f"the listed vehicle is {vehicle.value}")
        coverage_refs.append(ref_for(vehicle))
    if vin:
        coverage_bits.append(f"VIN {vin.value}")
        coverage_refs.append(ref_for(vin))
    if liability:
        coverage_bits.append(f"the main liability limits are {liability.value}")
        coverage_refs.append(ref_for(liability))
    if coverage_bits:
        points.append(f"Core coverage snapshot: {'; '.join(coverage_bits)}. {''.join(f'[{ref}]' for ref in coverage_refs)}")

    optional_bits: list[str] = []
    optional_refs: list[str] = []
    not_purchased: list[str] = []
    for label, fact in (
        ("collision", collision),
        ("comprehensive", comprehensive),
        ("rental reimbursement", rental),
    ):
        if not fact:
            continue
        value = fact.value
        if "not purchased" in value.lower():
            not_purchased.append(label)
        else:
            optional_bits.append(f"{label} is listed as {value}")
        optional_refs.append(ref_for(fact))
    if not_purchased:
        optional_bits.append(f"the following are listed as not purchased: {', '.join(not_purchased)}")

    policy_change = _first_fact(facts, "policy_change")
    change_effective_date = _first_fact(facts, "change_effective_date")
    discount_total = _first_fact(facts, "discount_total")
    optional_coverage = _first_fact(facts, "optional_coverage")
    identity_limit = _first_fact(facts, "identity_theft_limit")
    identity_deductible = _first_fact(facts, "identity_theft_deductible")
    not_full_policy = _first_fact(facts, "not_full_policy")

    if policy_change and change_effective_date:
        optional_bits.append(f"there is a policy change effective {change_effective_date.value}: {policy_change.value}")
        optional_refs.append(ref_for(policy_change))
    elif policy_change:
        optional_bits.append(f"there is a policy change: {policy_change.value}")
        optional_refs.append(ref_for(policy_change))
    if discount_total:
        optional_bits.append(f"discount savings are listed as {discount_total.value}")
        optional_refs.append(ref_for(discount_total))
    if optional_coverage:
        optional_bits.append(f"optional coverage includes {optional_coverage.value}")
        optional_refs.append(ref_for(optional_coverage))
    if identity_limit and identity_deductible:
        optional_bits.append(f"identity theft coverage has {identity_deductible.value} and a {identity_limit.value} limit")
        optional_refs.append(ref_for(identity_limit))
    elif identity_limit:
        optional_bits.append(f"identity theft coverage limit is {identity_limit.value}")
        optional_refs.append(ref_for(identity_limit))
    if not_full_policy:
        optional_bits.append(not_full_policy.value)
        optional_refs.append(ref_for(not_full_policy))
    if optional_bits:
        points.append(f"Important flags: {'; '.join(optional_bits)}. {''.join(f'[{ref}]' for ref in optional_refs)}")

    if not points:
        citations = fallback_citations(chunks, limit=3)
        for index, citation in enumerate(citations, start=1):
            location = f"page {citation.page_num}" if citation.page_num is not None else "the indexed document"
            section = f", section {citation.section}" if citation.section else ""
            points.append(
                f"Indexed source {index}: I found policy material from {citation.source_label} ({location}{section}). [S{index}]"
            )

    bullet_count = _requested_bullet_count(question)
    selected = points[:bullet_count]
    if len(selected) < bullet_count and points:
        selected = points

    answer = "Here are the main policy points I would pay attention to:\n" + "\n".join(
        f"{index}. {point}" for index, point in enumerate(selected, start=1)
    )
    return AnswerResponse(answer=answer, citations=citations, disclaimer="")


def _compact_case_context_excerpt(text: str, *, max_chars: int = 220) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        return "Saved accident context."

    if "Scene summary:" in cleaned:
        scene = cleaned.split("Scene summary:", 1)[1]
        for marker in ("Damage summary:", "Detailed narrative:", "Injuries reported:", "Police called:"):
            if marker in scene:
                scene = scene.split(marker, 1)[0]
                break
        cleaned = scene.strip(" .")
    else:
        for line in text.splitlines():
            if line.startswith("Accident summary:"):
                cleaned = line.removeprefix("Accident summary:").strip()
                break

    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip(" ,.;") + "..."


def _short_case_summary(context_chunk: RetrievedChunk) -> str:
    for line in context_chunk.chunk_text.splitlines():
        if line.startswith("Accident summary:"):
            return _compact_case_context_excerpt(line)
    return _compact_case_context_excerpt(context_chunk.chunk_text)


def _build_accident_coverage_answer(
    question: str,
    chunks: Sequence[RetrievedChunk],
    case_context: dict[str, Any] | None,
    *,
    case_id: str,
) -> AnswerResponse | None:
    if not is_accident_coverage_check_question(question):
        return None
    context_chunk = _case_context_chunk(case_id, case_context)
    if context_chunk is None or not chunks:
        return None

    facts = extract_policy_facts(chunks)
    citations: list[Citation] = []
    ref_keys: dict[tuple[str, str, int | None, str | None], str] = {}

    def ref_for_context() -> str:
        key = ("case_context", context_chunk.document_id or "", context_chunk.page_num, context_chunk.section)
        if key not in ref_keys:
            ref_keys[key] = f"S{len(citations) + 1}"
            citations.append(_chunk_citation(context_chunk))
        return ref_keys[key]

    def ref_for_fact(fact: PolicyFact) -> str:
        key = (fact.key, fact.value, fact.page_num, fact.section)
        if key not in ref_keys:
            ref_keys[key] = f"S{len(citations) + 1}"
            citations.append(_fact_citation(fact))
        return ref_keys[key]

    lines = [
        f"- Accident context: {_short_case_summary(context_chunk)} [{ref_for_context()}]"
    ]

    collision = _first_fact(facts, "collision_coverage")
    liability = _first_fact(facts, "liability_limits")
    rental = _first_fact(facts, "rental_reimbursement")
    comprehensive = _first_fact(facts, "comprehensive_coverage")

    if collision:
        lines.append(
            f"- First check collision coverage for damage to your own vehicle; this policy lists Auto Collision Insurance as {collision.value}. [{ref_for_fact(collision)}]"
        )
    if liability:
        lines.append(
            f"- Also review liability/property-damage limits because the accident involves another driver; the listed liability limits are {liability.value}. [{ref_for_fact(liability)}]"
        )
    if rental:
        lines.append(
            f"- If repairs leave you without a car, check rental reimbursement; the policy lists Rental Reimbursement as {rental.value}. [{ref_for_fact(rental)}]"
        )
    if comprehensive:
        lines.append(
            f"- Comprehensive coverage is usually separate from collision-type damage; this policy lists Auto Comprehensive Insurance as {comprehensive.value}. [{ref_for_fact(comprehensive)}]"
        )

    if len(lines) == 1:
        return None

    answer = (
        "Based on the saved accident context and the indexed policy, here are the coverage areas to check:\n"
        + "\n".join(lines)
        + "\nThis is a checklist, not a coverage guarantee; the insurer still has to apply the full policy terms to the claim."
    )
    return AnswerResponse(answer=answer, citations=citations, disclaimer="")


def _stringify_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(item).strip() for item in values if str(item).strip()]


def _format_party_rows(rows: object) -> list[str]:
    if not isinstance(rows, list):
        return []
    formatted: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        label = str(row.get("field_label") or "").strip()
        owner = str(row.get("owner_value") or "").strip()
        other = str(row.get("other_party_value") or "").strip()
        if label and (owner or other):
            formatted.append(f"{label}: owner={owner or 'Unknown'}; other_party={other or 'Unknown'}")
    return formatted


def _saved_case_context_text(case_context: dict[str, Any] | None) -> str | None:
    if not isinstance(case_context, dict):
        return None

    chat_context = case_context.get("chat_context")
    report_payload = case_context.get("report_payload")
    if not isinstance(chat_context, dict):
        chat_context = case_context if "summary" in case_context or "key_facts" in case_context else {}
    if not isinstance(report_payload, dict):
        report_payload = {}

    lines: list[str] = []
    summary = str(chat_context.get("summary") or report_payload.get("accident_summary") or "").strip()
    if summary:
        lines.append(f"Accident summary: {summary}")

    key_facts = _stringify_list(chat_context.get("key_facts"))
    if key_facts:
        lines.append("Key accident facts:")
        lines.extend(f"- {fact}" for fact in key_facts)

    party_rows = _format_party_rows(chat_context.get("party_comparison_rows") or report_payload.get("party_comparison_rows"))
    if party_rows:
        lines.append("Party comparison:")
        lines.extend(f"- {row}" for row in party_rows)

    for label, key in (
        ("Damage summary", "damage_summary"),
        ("Detailed narrative", "detailed_narrative"),
        ("Police report number", "police_report_number"),
        ("Repair shop", "repair_shop_name"),
        ("Adjuster", "adjuster_name"),
    ):
        value = str(report_payload.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")

    follow_up_items = _stringify_list(chat_context.get("follow_up_items") or report_payload.get("missing_items"))
    if follow_up_items:
        lines.append("Open follow-up items:")
        lines.extend(f"- {item}" for item in follow_up_items)

    if not lines:
        return None
    return "\n".join(lines)[:6000]


def _case_context_chunk(case_id: str, case_context: dict[str, Any] | None) -> RetrievedChunk | None:
    text = _saved_case_context_text(case_context)
    if not text:
        return None
    return RetrievedChunk(
        source_type="case_context",
        chunk_text=text,
        document_id="saved_accident_context",
        page_num=None,
        section="Saved Accident Context",
        metadata={"source_label": "Saved Accident Context", "case_id": case_id},
    )


async def _generate_rescue_answer(
    *,
    question: str,
    source_index: dict[str, object],
    client: AsyncOpenAI,
) -> str:
    response = await client.chat.completions.create(
        model=ai_config.rag_model,
        reasoning_effort=ai_config.rag_reasoning_effort,
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
        reasoning_effort=ai_config.rag_reasoning_effort,
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

    citations = citations_from_answer(raw_answer, source_index)
    if not _is_not_enough_info(raw_answer) and not citations:
        rescued_answer = await _generate_rescue_answer(
            question=question,
            source_index=source_index,
            client=openai_client,
        )
        rescued_citations = citations_from_answer(rescued_answer, source_index)
        if not _is_not_enough_info(rescued_answer) and rescued_citations:
            raw_answer = rescued_answer
            citations = rescued_citations
        else:
            raw_answer = NOT_ENOUGH_INFO_MESSAGE
            citations = fallback_citations(all_chunks)
    elif not citations:
        citations = fallback_citations(all_chunks)

    return AnswerResponse(
        answer=_normalize_answer(raw_answer),
        citations=citations,
        disclaimer=DISCLAIMER_FOOTER,
    )


async def answer_policy_question(
    case_id: str,
    question: str,
    *,
    client: AsyncOpenAI | None = None,
    case_context: dict[str, Any] | None = None,
) -> AnswerResponse:
    if case_context and is_accident_coverage_check_question(question):
        all_policy_chunks = await list_policy_chunks(case_id, limit=None)
        if coverage_answer := _build_accident_coverage_answer(
            question,
            all_policy_chunks,
            case_context,
            case_id=case_id,
        ):
            coverage_answer.answer = _normalize_answer(coverage_answer.answer)
            coverage_answer.disclaimer = DISCLAIMER_FOOTER
            return coverage_answer

    if is_policy_summary_question(question):
        all_policy_chunks = await list_policy_chunks(case_id, limit=None)
        if summary_answer := _build_summary_answer(question, all_policy_chunks):
            summary_answer.answer = _normalize_answer(summary_answer.answer)
            summary_answer.disclaimer = DISCLAIMER_FOOTER
            return summary_answer

    # Structured metadata questions are the most common demo path, so answer them
    # directly from the indexed policy corpus before spending an embedding call.
    if is_structured_policy_fact_question(question):
        all_policy_chunks = await list_policy_chunks(case_id, limit=None)
        if structured_answer := answer_structured_policy_question(question, all_policy_chunks):
            structured_answer.answer = _normalize_answer(structured_answer.answer)
            structured_answer.disclaimer = DISCLAIMER_FOOTER
            return structured_answer

    if is_structured_regulatory_question(question):
        kb_b_chunks = await list_kb_b_chunks(limit=None, document_ids=[CLAIM_ACK_RULE_DOCUMENT_ID])
        if structured_answer := answer_structured_regulatory_question(question, kb_b_chunks):
            structured_answer.answer = _normalize_answer(structured_answer.answer)
            structured_answer.disclaimer = DISCLAIMER_FOOTER
            return structured_answer

    query_embedding = await _embed_query(question)
    policy_chunks, regulatory_chunks = await asyncio.gather(
        search_case_chunks(case_id, query_embedding, top_k=ai_config.rag_top_k_per_source),
        search_kb_b_chunks(query_embedding, top_k=ai_config.rag_top_k_per_source),
    )
    if context_chunk := _case_context_chunk(case_id, case_context):
        policy_chunks = [context_chunk, *policy_chunks]

    # Only attempt structured extraction here for questions that did NOT already
    # go through the early structured path above (which uses the same full chunk
    # list and would have returned the same result).
    if policy_chunks and not is_structured_policy_fact_question(question):
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
    case_context: dict[str, Any] | None = None,
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
    if context_chunk := _case_context_chunk(case_id, case_context):
        policy_chunks = [context_chunk, *policy_chunks]
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

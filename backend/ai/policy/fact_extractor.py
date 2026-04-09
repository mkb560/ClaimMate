from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

from ai.ingestion.vector_store import RetrievedChunk
from ai.rag.citation_formatter import normalize_citation_section, source_label_for_chunk
from models.ai_types import AnswerResponse, Citation

POLICY_NUMBER_RE = re.compile(r"\b\d{3}\s\d{3}\s\d{3}\b|\b\d{9}\b")
POLICY_PERIOD_RE = re.compile(
    r"Policy period:\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})\s*[-–]\s*([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})",
    re.IGNORECASE,
)
DISCOUNT_TOTAL_RE = re.compile(
    r"discount savings(?:\s+for this policy period)?\s+are:\s*\$([0-9,]+\.\d{2})",
    re.IGNORECASE,
)
CHANGE_EFFECTIVE_RE = re.compile(
    r"The following change\(s\) are effective as of\s*([0-9/]+)\s*:\s*(.+?)(?:Your premium|Your discount savings|How to contact us|$)",
    re.IGNORECASE | re.DOTALL,
)
UNDERWRITTEN_BY_RE = re.compile(r"Underwritten by:\s*(.+?)(?:Policyholders:|Page \d+ of \d+|Customer Service|$)", re.IGNORECASE | re.DOTALL)
OPTIONAL_COVERAGE_RE = re.compile(r"Identity Theft Expenses Coverage", re.IGNORECASE)
VERIFICATION_RE = re.compile(r"Verification of Insurance", re.IGNORECASE)
RENEWAL_RE = re.compile(r"renewal offer", re.IGNORECASE)
POLICY_CHANGE_RE = re.compile(r"policy change", re.IGNORECASE)
POLICYHOLDERS_BLOCK_RE = re.compile(
    r"Policyholder\(s\)\s+(.+?)(?:Policy number|Your Allstate agency is|Page \d+ of \d+|$)",
    re.IGNORECASE | re.DOTALL,
)
POLICYHOLDERS_COLON_RE = re.compile(
    r"Policyholders:\s+(.+?)(?:Page \d+ of \d+|March \d{1,2}, \d{4}|Customer Service|$)",
    re.IGNORECASE | re.DOTALL,
)
NOT_FULL_POLICY_RE = re.compile(
    r"not an insurance policy and does not amend, extend or alter the coverage",
    re.IGNORECASE,
)
VEHICLE_LINE_RE = re.compile(
    r"\b(20\d{2}\s+[A-Za-z]+(?:\s+[A-Za-z]+){0,3})\s+([A-HJ-NPR-Z0-9]{17})\s+\$",
    re.IGNORECASE,
)
VEHICLE_LABEL_RE = re.compile(r"Vehicle:\s*(20\d{2}\s+[A-Za-z0-9 -]+)", re.IGNORECASE)
VIN_LABEL_RE = re.compile(r"(?:Vehicle identification number|VIN)\s*:?\s*([A-HJ-NPR-Z0-9]{17})", re.IGNORECASE)
LIABILITY_LIMITS_RE = re.compile(
    r"Automobile Liability Insurance.*?Bodily Injury\s+(\$[0-9,]+ each person)\s+(\$[0-9,]+ each occurrence)"
    r".*?Property Damage\s+(\$[0-9,]+ each occurrence)",
    re.IGNORECASE | re.DOTALL,
)
COLLISION_STATUS_RE = re.compile(r"Auto Collision Insurance\s+([^\n]+)", re.IGNORECASE)
COMPREHENSIVE_STATUS_RE = re.compile(r"Auto Comprehensive Insurance\s+([^\n]+)", re.IGNORECASE)
RENTAL_STATUS_RE = re.compile(r"Rental Reimbursement\s+([^\n]+)", re.IGNORECASE)
IDENTITY_THEFT_LIMIT_RE = re.compile(
    r"Identity Theft Expenses Coverage.*?up to a coverage limit of\s*(\$[0-9,]+)",
    re.IGNORECASE | re.DOTALL,
)
IDENTITY_THEFT_DEDUCTIBLE_RE = re.compile(
    r"Identity Theft Expenses Coverage.*?\b(no deductible|\$[0-9,]+ deductible)\b",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(slots=True)
class PolicyFact:
    key: str
    value: str
    page_num: int | None
    section: str | None
    source_label: str
    excerpt: str


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_fact_value(text: str) -> str:
    return _normalize_space(text.replace("*", "").rstrip("."))


def _with_indefinite_article(text: str) -> str:
    article = "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
    return f"{article} {text}"


def _find_matches(pattern: re.Pattern[str], chunks: Sequence[RetrievedChunk]) -> list[tuple[RetrievedChunk, re.Match[str]]]:
    matches: list[tuple[RetrievedChunk, re.Match[str]]] = []
    for chunk in chunks:
        match = pattern.search(chunk.chunk_text)
        if match:
            matches.append((chunk, match))
    return matches


def _make_fact(key: str, value: str, chunk: RetrievedChunk, excerpt: str) -> PolicyFact:
    return PolicyFact(
        key=key,
        value=_clean_fact_value(value),
        page_num=chunk.page_num,
        section=chunk.section,
        source_label=source_label_for_chunk(chunk),
        excerpt=_normalize_space(excerpt)[:160],
    )


def _group_possible_names(raw_text: str) -> list[str]:
    cleaned = _normalize_space(raw_text.replace("•", " "))
    tokens = cleaned.split()
    name_tokens: list[str] = []
    for token in tokens:
        if re.search(r"\d", token):
            break
        if token.lower() in {"policy", "number", "page", "customer", "service"}:
            break
        name_tokens.append(token)

    if len(name_tokens) < 2:
        return []

    names: list[str] = []
    index = 0
    while index + 1 < len(name_tokens):
        first = name_tokens[index]
        second = name_tokens[index + 1]
        if first[:1].isupper() and second[:1].isupper():
            names.append(f"{first} {second}")
            index += 2
        else:
            index += 1

    deduped: list[str] = []
    for name in names:
        if name not in deduped:
            deduped.append(name)
    return deduped


def extract_policy_facts(chunks: Sequence[RetrievedChunk]) -> dict[str, list[PolicyFact]]:
    facts: dict[str, list[PolicyFact]] = {}

    for chunk, match in _find_matches(POLICYHOLDERS_BLOCK_RE, chunks):
        names = _group_possible_names(match.group(1))
        if names:
            facts.setdefault("policyholders", []).append(
                _make_fact("policyholders", ", ".join(names), chunk, match.group(0))
            )

    for chunk, match in _find_matches(POLICYHOLDERS_COLON_RE, chunks):
        names = _group_possible_names(match.group(1))
        if names:
            facts.setdefault("policyholders", []).append(
                _make_fact("policyholders", ", ".join(names), chunk, match.group(0))
            )

    for chunk in chunks:
        if "Policy number" in chunk.chunk_text or "Policy Number" in chunk.chunk_text:
            tail = chunk.chunk_text.split("Policy number", 1)[-1]
            candidates = POLICY_NUMBER_RE.findall(tail)
            if candidates:
                facts.setdefault("policy_number", []).append(
                    _make_fact("policy_number", candidates[-1], chunk, tail)
                )
        elif "Policy Number:" in chunk.chunk_text:
            candidates = POLICY_NUMBER_RE.findall(chunk.chunk_text)
            if candidates:
                facts.setdefault("policy_number", []).append(
                    _make_fact("policy_number", candidates[-1], chunk, chunk.chunk_text)
                )

    for chunk, match in _find_matches(POLICY_PERIOD_RE, chunks):
        facts.setdefault("policy_period", []).append(
            _make_fact("policy_period", f"{match.group(1)} to {match.group(2)}", chunk, match.group(0))
        )

    for chunk, match in _find_matches(DISCOUNT_TOTAL_RE, chunks):
        facts.setdefault("discount_total", []).append(
            _make_fact("discount_total", f"${match.group(1)}", chunk, match.group(0))
        )

    for chunk, match in _find_matches(CHANGE_EFFECTIVE_RE, chunks):
        change_summary = _normalize_space(match.group(2)).rstrip(".")
        facts.setdefault("policy_change", []).append(
            _make_fact("policy_change", change_summary, chunk, match.group(0))
        )
        facts.setdefault("change_effective_date", []).append(
            _make_fact("change_effective_date", match.group(1), chunk, match.group(0))
        )

    for chunk, match in _find_matches(UNDERWRITTEN_BY_RE, chunks):
        facts.setdefault("insurer", []).append(
            _make_fact("insurer", match.group(1), chunk, match.group(0))
        )

    for chunk, match in _find_matches(VEHICLE_LINE_RE, chunks):
        facts.setdefault("vehicle_description", []).append(
            _make_fact("vehicle_description", match.group(1), chunk, match.group(0))
        )
        facts.setdefault("vehicle_vin", []).append(
            _make_fact("vehicle_vin", match.group(2), chunk, match.group(0))
        )

    for chunk, match in _find_matches(VEHICLE_LABEL_RE, chunks):
        facts.setdefault("vehicle_description", []).append(
            _make_fact("vehicle_description", match.group(1), chunk, match.group(0))
        )

    for chunk, match in _find_matches(VIN_LABEL_RE, chunks):
        facts.setdefault("vehicle_vin", []).append(
            _make_fact("vehicle_vin", match.group(1), chunk, match.group(0))
        )

    for chunk, match in _find_matches(LIABILITY_LIMITS_RE, chunks):
        bodily_injury = f"{match.group(1)} / {match.group(2)}"
        property_damage = match.group(3)
        facts.setdefault("liability_limits", []).append(
            _make_fact(
                "liability_limits",
                f"Bodily Injury Liability {bodily_injury}; Property Damage Liability {property_damage}",
                chunk,
                match.group(0),
            )
        )

    for key, pattern in (
        ("collision_coverage", COLLISION_STATUS_RE),
        ("comprehensive_coverage", COMPREHENSIVE_STATUS_RE),
        ("rental_reimbursement", RENTAL_STATUS_RE),
    ):
        for chunk, match in _find_matches(pattern, chunks):
            facts.setdefault(key, []).append(
                _make_fact(key, match.group(1), chunk, match.group(0))
            )

    for chunk, match in _find_matches(IDENTITY_THEFT_LIMIT_RE, chunks):
        facts.setdefault("identity_theft_limit", []).append(
            _make_fact("identity_theft_limit", match.group(1), chunk, match.group(0))
        )

    for chunk, match in _find_matches(IDENTITY_THEFT_DEDUCTIBLE_RE, chunks):
        facts.setdefault("identity_theft_deductible", []).append(
            _make_fact("identity_theft_deductible", match.group(1), chunk, match.group(0))
        )

    for chunk in chunks:
        if OPTIONAL_COVERAGE_RE.search(chunk.chunk_text):
            facts.setdefault("optional_coverage", []).append(
                _make_fact("optional_coverage", "Identity Theft Expenses Coverage", chunk, chunk.chunk_text)
            )
        if VERIFICATION_RE.search(chunk.chunk_text):
            facts.setdefault("document_type", []).append(
                _make_fact("document_type", "verification of insurance", chunk, chunk.chunk_text)
            )
        elif RENEWAL_RE.search(chunk.chunk_text):
            facts.setdefault("document_type", []).append(
                _make_fact("document_type", "auto insurance renewal package", chunk, chunk.chunk_text)
            )
        elif POLICY_CHANGE_RE.search(chunk.chunk_text):
            facts.setdefault("document_type", []).append(
                _make_fact("document_type", "policy change confirmation packet", chunk, chunk.chunk_text)
            )
        if NOT_FULL_POLICY_RE.search(chunk.chunk_text):
            facts.setdefault("not_full_policy", []).append(
                _make_fact("not_full_policy", "This document is only verification of insurance, not the full policy.", chunk, chunk.chunk_text)
            )

    return facts


def _first_fact(facts: dict[str, list[PolicyFact]], key: str) -> PolicyFact | None:
    values = facts.get(key) or []
    return values[0] if values else None


def detect_requested_policy_fact_keys(question: str) -> set[str]:
    lowered = question.lower()
    keys: set[str] = set()
    if (
        "policyholder" in lowered
        or "policyholders" in lowered
        or "named insured" in lowered
        or ("who" in lowered and ("policy" in lowered or "insured" in lowered))
    ):
        keys.add("policyholders")
    if "policy number" in lowered:
        keys.add("policy_number")
    if (
        ("policy period" in lowered and "for this policy period" not in lowered and "discount" not in lowered)
        or ("effective" in lowered and "change" not in lowered)
    ):
        keys.add("policy_period")
    if "insurer" in lowered or "underwritten" in lowered or "company" in lowered or "carrier" in lowered:
        keys.add("insurer")
    if "change" in lowered:
        keys.update({"policy_change", "change_effective_date"})
    if "discount" in lowered:
        keys.add("discount_total")
    if "optional coverage" in lowered or "highlight" in lowered or "identity theft" in lowered:
        keys.add("optional_coverage")
    if "identity theft" in lowered and ("limit" in lowered or "deductible" in lowered or "coverage" in lowered):
        keys.update({"identity_theft_limit", "identity_theft_deductible"})
    if "what kind of" in lowered or "renewal" in lowered or "packet" in lowered or "document" in lowered:
        keys.add("document_type")
    if "full insurance policy" in lowered or (
        "verification of insurance" in lowered
        and any(term in lowered for term in ("only", "full", "document", "policy"))
    ):
        keys.update({"document_type", "not_full_policy"})
    if "rental reimbursement" in lowered:
        keys.add("rental_reimbursement")
    if "collision" in lowered:
        keys.add("collision_coverage")
        if "deductible" in lowered:
            keys.add("collision_deductible")
    if "comprehensive" in lowered:
        keys.add("comprehensive_coverage")
        if "deductible" in lowered:
            keys.add("comprehensive_deductible")
    if "liability" in lowered and ("limit" in lowered or "limits" in lowered or "coverage" in lowered):
        keys.add("liability_limits")
    if "vehicle" in lowered:
        keys.add("vehicle_description")
    if re.search(r"\bvin\b", lowered) or "vehicle identification number" in lowered:
        keys.add("vehicle_vin")
    return keys


def is_structured_policy_fact_question(question: str) -> bool:
    return bool(detect_requested_policy_fact_keys(question))


def _fact_to_citation(fact: PolicyFact) -> Citation:
    return Citation(
        source_type="kb_a",
        source_label=fact.source_label,
        document_id="policy_pdf",
        page_num=fact.page_num,
        section=normalize_citation_section(fact.section),
        excerpt=fact.excerpt,
    )


def _build_fact_answer(requested_keys: set[str], facts: dict[str, list[PolicyFact]]) -> AnswerResponse | None:
    fact_to_ref: dict[tuple[str, int | None, str | None], str] = {}
    citations: list[Citation] = []
    remaining_keys = set(requested_keys)

    def ref_for(fact: PolicyFact) -> str:
        key = (fact.source_label, fact.page_num, fact.section)
        if key not in fact_to_ref:
            fact_to_ref[key] = f"S{len(fact_to_ref) + 1}"
            citations.append(_fact_to_citation(fact))
        return fact_to_ref[key]

    lines: list[str] = []

    policyholders = _first_fact(facts, "policyholders")
    policy_number = _first_fact(facts, "policy_number")
    if {"policyholders", "policy_number"} <= remaining_keys and policyholders and policy_number:
        lines.append(
            f"The policyholders listed in the document are {policyholders.value}. [{ref_for(policyholders)}] "
            f"The policy number is {policy_number.value}. [{ref_for(policy_number)}]"
        )
        remaining_keys -= {"policyholders", "policy_number"}

    document_type = _first_fact(facts, "document_type")
    if {"document_type", "policyholders"} <= remaining_keys and document_type and policyholders:
        lines.append(
            f"This document is {_with_indefinite_article(document_type.value)}. [{ref_for(document_type)}] "
            f"The policyholders listed in the document are {policyholders.value}. [{ref_for(policyholders)}]"
        )
        remaining_keys -= {"document_type", "policyholders"}

    policy_period = _first_fact(facts, "policy_period")
    insurer = _first_fact(facts, "insurer")
    if {"policy_number", "policy_period", "insurer"} <= remaining_keys and policy_number and policy_period and insurer:
        lines.append(
            f"The policy number is {policy_number.value}. [{ref_for(policy_number)}] "
            f"The policy period is {policy_period.value}. [{ref_for(policy_period)}] "
            f"The insurer listed in the document is {insurer.value}. [{ref_for(insurer)}]"
        )
        remaining_keys -= {"policy_number", "policy_period", "insurer"}

    if "document_type" in remaining_keys and document_type:
        lines.append(f"This document is {_with_indefinite_article(document_type.value)}. [{ref_for(document_type)}]")
        remaining_keys.remove("document_type")

    not_full_policy = _first_fact(facts, "not_full_policy")
    if "not_full_policy" in remaining_keys and not_full_policy:
        lines.append(f"{not_full_policy.value} [{ref_for(not_full_policy)}]")
        remaining_keys.remove("not_full_policy")

    if "policyholders" in remaining_keys and policyholders:
        lines.append(f"The policyholders listed in the document are {policyholders.value}. [{ref_for(policyholders)}]")
        remaining_keys.remove("policyholders")

    if "policy_number" in remaining_keys and policy_number:
        lines.append(f"The policy number is {policy_number.value}. [{ref_for(policy_number)}]")
        remaining_keys.remove("policy_number")

    if {"policy_period", "insurer"} & remaining_keys:
        if policy_period and insurer:
            lines.append(
                f"The policy period is {policy_period.value}, and the insurer listed in the document is {insurer.value}. "
                f"[{ref_for(policy_period)}][{ref_for(insurer)}]"
            )
            remaining_keys -= {"policy_period", "insurer"}
        elif policy_period:
            lines.append(f"The policy period is {policy_period.value}. [{ref_for(policy_period)}]")
            remaining_keys.remove("policy_period")
        elif insurer:
            lines.append(f"The insurer listed in the document is {insurer.value}. [{ref_for(insurer)}]")
            remaining_keys.remove("insurer")

    policy_change = _first_fact(facts, "policy_change")
    change_effective_date = _first_fact(facts, "change_effective_date")
    if {"policy_change", "change_effective_date"} & remaining_keys and policy_change and change_effective_date:
        lines.append(
            f"The document confirms the following policy change: {policy_change.value}. It is effective {change_effective_date.value}. "
            f"[{ref_for(policy_change)}]"
        )
        remaining_keys -= {"policy_change", "change_effective_date"}

    discount_total = _first_fact(facts, "discount_total")
    if "discount_total" in remaining_keys and discount_total:
        lines.append(f"The document lists total discount savings of {discount_total.value} for the policy period. [{ref_for(discount_total)}]")
        remaining_keys.remove("discount_total")

    optional_coverage = _first_fact(facts, "optional_coverage")
    if "optional_coverage" in remaining_keys and optional_coverage:
        lines.append(f"The optional coverage highlighted in this document is {optional_coverage.value}. [{ref_for(optional_coverage)}]")
        remaining_keys.remove("optional_coverage")

    collision_coverage = _first_fact(facts, "collision_coverage")
    if "collision_coverage" in remaining_keys and collision_coverage:
        lines.append(
            f"Auto Collision Insurance is listed as {collision_coverage.value}. [{ref_for(collision_coverage)}]"
        )
        remaining_keys.remove("collision_coverage")

    if "collision_deductible" in remaining_keys and collision_coverage:
        if collision_coverage.value.lower() == "not purchased":
            lines.append(
                f"Auto Collision Insurance is listed as {collision_coverage.value}, so no collision deductible amount is shown. "
                f"[{ref_for(collision_coverage)}]"
            )
        else:
            lines.append(
                f"Auto Collision Insurance is listed as {collision_coverage.value}. [{ref_for(collision_coverage)}]"
            )
        remaining_keys.remove("collision_deductible")

    comprehensive_coverage = _first_fact(facts, "comprehensive_coverage")
    if "comprehensive_coverage" in remaining_keys and comprehensive_coverage:
        lines.append(
            f"Auto Comprehensive Insurance is listed as {comprehensive_coverage.value}. "
            f"[{ref_for(comprehensive_coverage)}]"
        )
        remaining_keys.remove("comprehensive_coverage")

    if "comprehensive_deductible" in remaining_keys and comprehensive_coverage:
        if comprehensive_coverage.value.lower() == "not purchased":
            lines.append(
                f"Auto Comprehensive Insurance is listed as {comprehensive_coverage.value}, so no comprehensive deductible amount is shown. "
                f"[{ref_for(comprehensive_coverage)}]"
            )
        else:
            lines.append(
                f"Auto Comprehensive Insurance is listed as {comprehensive_coverage.value}. "
                f"[{ref_for(comprehensive_coverage)}]"
            )
        remaining_keys.remove("comprehensive_deductible")

    rental_reimbursement = _first_fact(facts, "rental_reimbursement")
    if "rental_reimbursement" in remaining_keys and rental_reimbursement:
        lines.append(
            f"The Coverage Detail section lists Rental Reimbursement as {rental_reimbursement.value}. "
            f"[{ref_for(rental_reimbursement)}]"
        )
        remaining_keys.remove("rental_reimbursement")

    liability_limits = _first_fact(facts, "liability_limits")
    if "liability_limits" in remaining_keys and liability_limits:
        lines.append(f"The listed liability limits are {liability_limits.value}. [{ref_for(liability_limits)}]")
        remaining_keys.remove("liability_limits")

    vehicle_description = _first_fact(facts, "vehicle_description")
    vehicle_vin = _first_fact(facts, "vehicle_vin")
    if {"vehicle_description", "vehicle_vin"} <= remaining_keys and vehicle_description and vehicle_vin:
        lines.append(
            f"The listed vehicle is {vehicle_description.value}, and the VIN is {vehicle_vin.value}. "
            f"[{ref_for(vehicle_description)}][{ref_for(vehicle_vin)}]"
        )
        remaining_keys -= {"vehicle_description", "vehicle_vin"}
    else:
        if "vehicle_description" in remaining_keys and vehicle_description:
            lines.append(f"The listed vehicle is {vehicle_description.value}. [{ref_for(vehicle_description)}]")
            remaining_keys.remove("vehicle_description")
        if "vehicle_vin" in remaining_keys and vehicle_vin:
            lines.append(f"The VIN listed in the document is {vehicle_vin.value}. [{ref_for(vehicle_vin)}]")
            remaining_keys.remove("vehicle_vin")

    identity_theft_limit = _first_fact(facts, "identity_theft_limit")
    identity_theft_deductible = _first_fact(facts, "identity_theft_deductible")
    if {"identity_theft_limit", "identity_theft_deductible"} <= remaining_keys and identity_theft_limit and identity_theft_deductible:
        lines.append(
            f"Identity Theft Expenses Coverage is described as having {identity_theft_deductible.value} and a coverage limit of "
            f"{identity_theft_limit.value}. [{ref_for(identity_theft_limit)}]"
        )
        remaining_keys -= {"identity_theft_limit", "identity_theft_deductible"}
    else:
        if "identity_theft_limit" in remaining_keys and identity_theft_limit:
            lines.append(
                f"Identity Theft Expenses Coverage is described as having a coverage limit of {identity_theft_limit.value}. "
                f"[{ref_for(identity_theft_limit)}]"
            )
            remaining_keys.remove("identity_theft_limit")
        if "identity_theft_deductible" in remaining_keys and identity_theft_deductible:
            lines.append(
                f"Identity Theft Expenses Coverage is described as having {identity_theft_deductible.value}. "
                f"[{ref_for(identity_theft_deductible)}]"
            )
            remaining_keys.remove("identity_theft_deductible")

    if not lines or remaining_keys:
        return None

    return AnswerResponse(
        answer=" ".join(lines),
        citations=citations,
        disclaimer="",
    )


def answer_structured_policy_question(question: str, chunks: Sequence[RetrievedChunk]) -> AnswerResponse | None:
    requested_keys = detect_requested_policy_fact_keys(question)
    if not requested_keys:
        return None
    facts = extract_policy_facts(chunks)
    return _build_fact_answer(requested_keys, facts)

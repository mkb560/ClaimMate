from __future__ import annotations

import re

SOURCE_LABELS = {
    "policy_pdf": "Your Policy",
    "ca_fair_claims": "California Fair Claims Regulations",
    "iso_pp_0001": "ISO Personal Auto Policy",
    "naic_model_900": "NAIC Model 900",
    "naic_model_902": "NAIC Model 902",
    "iii_nofault": "Insurance Information Institute",
    "naic_complaints": "NAIC Complaint Data",
    "ca_reg_2695_2_definitions": "10 CCR 2695.2 Definitions",
    "ca_reg_2695_3_file_record_documentation": "10 CCR 2695.3 File and Record Documentation",
    "ca_reg_2695_4_policy_provisions_benefits": "10 CCR 2695.4 Policy Provisions and Benefits",
    "ca_reg_2695_5_duties_upon_receipt_of_communications": "10 CCR 2695.5 Duties Upon Receipt of Communications",
    "ca_reg_2695_7_prompt_fair_equitable_settlements": "10 CCR 2695.7 Prompt, Fair, and Equitable Settlements",
    "ca_reg_2695_85_auto_body_repair_consumer_bill_of_rights": "10 CCR 2695.85 Auto Body Repair Consumer Bill of Rights",
    "ca_reg_2695_8_auto_insurance_standards": "10 CCR 2695.8 Automobile Insurance Claim Standards",
    "ca_accident_whats_next_2024": "California Accident Guide: What's Next (2024)",
    "ca_auto_insurance_guide_2025": "California Auto Insurance Guide (2025)",
    "ca_claims_mediation_program": "California Claims Mediation Program",
    "naic_consumer_guide_auto_claims": "NAIC Consumer Guide to Auto Claims",
}

DISPUTE_RELEVANT_DOCUMENT_IDS = (
    "ca_fair_claims",
    "naic_model_900",
    "naic_model_902",
    "ca_reg_2695_2_definitions",
    "ca_reg_2695_3_file_record_documentation",
    "ca_reg_2695_4_policy_provisions_benefits",
    "ca_reg_2695_5_duties_upon_receipt_of_communications",
    "ca_reg_2695_7_prompt_fair_equitable_settlements",
    "ca_reg_2695_85_auto_body_repair_consumer_bill_of_rights",
    "ca_reg_2695_8_auto_insurance_standards",
    "ca_claims_mediation_program",
    "naic_consumer_guide_auto_claims",
)

_YEAR_SUFFIX_RE = re.compile(r"_(20\d{2})$")


def _humanize_document_id(document_id: str) -> str:
    text = document_id.replace("_", " ").strip()
    text = re.sub(r"\bca\b", "CA", text, flags=re.IGNORECASE)
    text = re.sub(r"\bnaic\b", "NAIC", text, flags=re.IGNORECASE)
    text = re.sub(r"\biso\b", "ISO", text, flags=re.IGNORECASE)

    year_match = _YEAR_SUFFIX_RE.search(document_id)
    if year_match:
        year = year_match.group(1)
        base = document_id[: -(len(year) + 1)].replace("_", " ").strip()
        base = re.sub(r"\bca\b", "CA", base, flags=re.IGNORECASE)
        base = re.sub(r"\bnaic\b", "NAIC", base, flags=re.IGNORECASE)
        base = re.sub(r"\biso\b", "ISO", base, flags=re.IGNORECASE)
        return f"{base.title()} ({year})"

    return text.title()


def source_label_for_document(document_id: str | None) -> str | None:
    if not document_id:
        return None
    return SOURCE_LABELS.get(document_id, _humanize_document_id(document_id))

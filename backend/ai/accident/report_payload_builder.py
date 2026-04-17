from __future__ import annotations

from datetime import UTC, datetime

from models.accident_types import (
    AccidentChatContext,
    AccidentReportPayload,
    PartyComparisonRow,
    PartyRecord,
    PhotoAttachment,
    StageAAccidentIntake,
    StageBAccidentIntake,
    TimelineEntry,
    VehicleRecord,
)


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.split()).strip()
    return normalized or None


def _format_bool(value: bool | None, *, true_label: str, false_label: str = "No", unknown_label: str = "Unknown") -> str:
    if value is True:
        return true_label
    if value is False:
        return false_label
    return unknown_label


def _format_vehicle(vehicle: VehicleRecord | None) -> str:
    if vehicle is None:
        return "Unknown"

    parts: list[str] = []
    if vehicle.year is not None:
        parts.append(str(vehicle.year))
    for value in (vehicle.make, vehicle.model, vehicle.color):
        cleaned = _clean_text(value)
        if cleaned:
            parts.append(cleaned)
    base = " ".join(parts) or "Unknown vehicle"
    if cleaned_plate := _clean_text(vehicle.license_plate):
        base = f"{base} (plate: {cleaned_plate})"
    return base


def _format_party_value(party: PartyRecord | None, selector: str) -> str:
    if party is None:
        return "Unknown"

    if selector == "name":
        return _clean_text(party.name) or "Unknown"
    if selector == "phone":
        return _clean_text(party.phone) or "Unknown"
    if selector == "insurer":
        return _clean_text(party.insurer) or "Unknown"
    if selector == "policy_number":
        return _clean_text(party.policy_number) or "Unknown"
    if selector == "claim_number":
        return _clean_text(party.claim_number) or "Unknown"
    if selector == "vehicle":
        return _format_vehicle(party.vehicle)
    raise ValueError(f"Unsupported selector: {selector}")


def _format_location(stage_a: StageAAccidentIntake) -> str | None:
    if stage_a.location is None:
        return None

    parts: list[str] = []
    if address := _clean_text(stage_a.location.address):
        parts.append(address)

    if stage_a.location.latitude is not None and stage_a.location.longitude is not None:
        parts.append(f"GPS {stage_a.location.latitude:.6f}, {stage_a.location.longitude:.6f}")

    return " | ".join(parts) if parts else None


def _build_summary(case_id: str, stage_a: StageAAccidentIntake, stage_b: StageBAccidentIntake | None) -> str:
    sentences: list[str] = [f"ClaimMate accident report for case {case_id}."]

    if stage_a.occurred_at is not None:
        sentences.append(f"Reported accident time: {stage_a.occurred_at.isoformat()}.")

    location_summary = _format_location(stage_a)
    if location_summary:
        sentences.append(f"Reported location: {location_summary}.")

    owner_name = _format_party_value(stage_a.owner_party, "name")
    other_name = _format_party_value(stage_a.other_party, "name")
    sentences.append(f"Owner party: {owner_name}.")
    if other_name != "Unknown":
        sentences.append(f"Other party: {other_name}.")

    if quick_summary := _clean_text(stage_a.quick_summary):
        sentences.append(f"Scene summary: {quick_summary}.")

    if stage_b is not None:
        if damage_summary := _clean_text(stage_b.damage_summary):
            sentences.append(f"Damage summary: {damage_summary}.")
        if narrative := _clean_text(stage_b.detailed_narrative):
            sentences.append(f"Detailed narrative: {narrative}.")

    sentences.append(
        "Injuries reported: "
        + _format_bool(stage_a.injuries_reported, true_label="Yes", false_label="No")
        + "."
    )
    sentences.append(
        "Police called: "
        + _format_bool(stage_a.police_called, true_label="Yes", false_label="No")
        + "."
    )

    return " ".join(sentences)


def _build_party_comparison(stage_a: StageAAccidentIntake) -> list[PartyComparisonRow]:
    rows: list[PartyComparisonRow] = []
    for label, selector in (
        ("Party name", "name"),
        ("Phone", "phone"),
        ("Insurer", "insurer"),
        ("Policy number", "policy_number"),
        ("Claim number", "claim_number"),
        ("Vehicle", "vehicle"),
    ):
        rows.append(
            PartyComparisonRow(
                field_label=label,
                owner_value=_format_party_value(stage_a.owner_party, selector),
                other_party_value=_format_party_value(stage_a.other_party, selector),
            )
        )
    return rows


def _build_timeline(
    stage_a: StageAAccidentIntake,
    stage_b: StageBAccidentIntake | None,
    generated_at: datetime,
) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []
    if stage_a.occurred_at is not None:
        entries.append(TimelineEntry(label="Accident occurred", timestamp=stage_a.occurred_at))
    if stage_a.stage_completed_at is not None:
        entries.append(TimelineEntry(label="Stage A completed", timestamp=stage_a.stage_completed_at))
    if stage_b is not None and stage_b.stage_completed_at is not None:
        entries.append(TimelineEntry(label="Stage B completed", timestamp=stage_b.stage_completed_at))
    entries.append(TimelineEntry(label="Accident report generated", timestamp=generated_at))
    return entries


def _build_missing_items(stage_a: StageAAccidentIntake, stage_b: StageBAccidentIntake | None, photos: list[PhotoAttachment]) -> list[str]:
    missing: list[str] = []

    if stage_a.location is None or (
        _clean_text(stage_a.location.address) is None
        and (stage_a.location.latitude is None or stage_a.location.longitude is None)
    ):
        missing.append("Accident location is incomplete.")

    if stage_a.other_party is None or _clean_text(stage_a.other_party.name) is None:
        missing.append("Other party information is incomplete.")

    if not photos:
        missing.append("No accident photos have been uploaded yet.")

    if stage_b is None:
        missing.append("Stage B home follow-up details have not been completed yet.")
        return missing

    if _clean_text(stage_b.damage_summary) is None:
        missing.append("Detailed damage summary is missing.")

    if stage_a.police_called and _clean_text(stage_b.police_report_number) is None:
        missing.append("Police report number is missing.")

    if stage_a.injuries_reported and not stage_b.witness_contacts:
        missing.append("Witness or injury follow-up notes are still missing.")

    return missing


def build_accident_report_payload(
    case_id: str,
    stage_a: StageAAccidentIntake,
    stage_b: StageBAccidentIntake | None = None,
    *,
    generated_at: datetime | None = None,
    report_title: str | None = None,
) -> AccidentReportPayload:
    resolved_generated_at = generated_at or datetime.now(UTC)
    resolved_title = report_title or f"ClaimMate Accident Report - {case_id}"
    photo_attachments = [*stage_a.photo_attachments, *(stage_b.additional_photos if stage_b is not None else [])]

    return AccidentReportPayload(
        case_id=case_id,
        report_title=resolved_title,
        generated_at=resolved_generated_at,
        accident_summary=_build_summary(case_id, stage_a, stage_b),
        occurrence_time=stage_a.occurred_at,
        location_summary=_format_location(stage_a),
        owner_party=stage_a.owner_party,
        other_party=stage_a.other_party,
        detailed_narrative=_clean_text(stage_b.detailed_narrative if stage_b is not None else None) or "",
        damage_summary=_clean_text(stage_b.damage_summary if stage_b is not None else None),
        injuries_reported=stage_a.injuries_reported,
        police_called=stage_a.police_called,
        drivable=stage_a.drivable,
        tow_requested=stage_a.tow_requested,
        weather_conditions=_clean_text(stage_b.weather_conditions if stage_b is not None else None),
        road_conditions=_clean_text(stage_b.road_conditions if stage_b is not None else None),
        witness_contacts=list(stage_b.witness_contacts) if stage_b is not None else [],
        police_report_number=_clean_text(stage_b.police_report_number if stage_b is not None else None),
        adjuster_name=_clean_text(stage_b.adjuster_name if stage_b is not None else None),
        repair_shop_name=_clean_text(stage_b.repair_shop_name if stage_b is not None else None),
        photo_attachments=photo_attachments,
        party_comparison_rows=_build_party_comparison(stage_a),
        timeline_entries=_build_timeline(stage_a, stage_b, resolved_generated_at),
        missing_items=_build_missing_items(stage_a, stage_b, photo_attachments),
    )


def build_accident_chat_context(report_payload: AccidentReportPayload) -> AccidentChatContext:
    key_facts: list[str] = []

    if report_payload.location_summary:
        key_facts.append(f"Location: {report_payload.location_summary}")
    if report_payload.occurrence_time is not None:
        key_facts.append(f"Accident time: {report_payload.occurrence_time.isoformat()}")
    key_facts.append(
        "Police called: "
        + _format_bool(report_payload.police_called, true_label="Yes", false_label="No")
    )
    key_facts.append(
        "Injuries reported: "
        + _format_bool(report_payload.injuries_reported, true_label="Yes", false_label="No")
    )
    key_facts.append(f"Photos attached: {len(report_payload.photo_attachments)}")

    return AccidentChatContext(
        case_id=report_payload.case_id,
        pinned_document_title=report_payload.report_title,
        summary=report_payload.accident_summary,
        key_facts=key_facts,
        party_comparison_rows=list(report_payload.party_comparison_rows),
        follow_up_items=list(report_payload.missing_items),
        generated_at=report_payload.generated_at,
    )

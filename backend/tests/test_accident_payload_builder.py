from datetime import UTC, datetime

from ai.accident.report_payload_builder import build_accident_chat_context, build_accident_report_payload
from models.accident_types import (
    LocationSnapshot,
    PartyRecord,
    PartyRole,
    PhotoAttachment,
    PhotoCategory,
    StageAAccidentIntake,
    StageBAccidentIntake,
    VehicleRecord,
    WitnessRecord,
)


def test_build_accident_report_payload_merges_stage_inputs() -> None:
    stage_a = StageAAccidentIntake(
        occurred_at=datetime(2026, 3, 30, 18, 5, tzinfo=UTC),
        location=LocationSnapshot(
            address="123 Figueroa St, Los Angeles, CA",
            latitude=34.0407,
            longitude=-118.2468,
        ),
        owner_party=PartyRecord(
            role=PartyRole.OWNER,
            name="Mingtao Ding",
            phone="213-555-0100",
            insurer="Allstate",
            policy_number="804 448 188",
            vehicle=VehicleRecord(year=2022, make="Tesla", model="Model 3", color="Blue", license_plate="8ABC123"),
        ),
        other_party=PartyRecord(
            role=PartyRole.OTHER_DRIVER,
            name="Alex Kim",
            phone="310-555-2200",
            insurer="Progressive",
            policy_number="P-7788",
            claim_number="CLM-22",
            vehicle=VehicleRecord(year=2021, make="Toyota", model="Camry", color="White", license_plate="9XYZ999"),
        ),
        injuries_reported=False,
        police_called=True,
        drivable=False,
        tow_requested=True,
        quick_summary="Rear-end collision at a red light.",
        photo_attachments=[
            PhotoAttachment(
                photo_id="photo-1",
                category=PhotoCategory.OVERVIEW,
                storage_key="cases/case-1/photo-1.jpg",
                caption="Wide shot of both vehicles",
            )
        ],
        stage_completed_at=datetime(2026, 3, 30, 18, 15, tzinfo=UTC),
    )
    stage_b = StageBAccidentIntake(
        detailed_narrative="Owner was stopped at the light when the other driver struck the rear bumper.",
        damage_summary="Rear bumper crushed and trunk misaligned.",
        weather_conditions="Clear",
        road_conditions="Dry",
        witness_contacts=[WitnessRecord(name="Jamie Lee", phone="626-555-1111")],
        police_report_number="LAPD-2026-0001",
        adjuster_name="Pat Morgan",
        repair_shop_name="USC Auto Body",
        additional_photos=[
            PhotoAttachment(
                photo_id="photo-2",
                category=PhotoCategory.OWNER_DAMAGE,
                storage_key="cases/case-1/photo-2.jpg",
                caption="Rear bumper damage",
            )
        ],
        stage_completed_at=datetime(2026, 3, 30, 22, 0, tzinfo=UTC),
    )

    report = build_accident_report_payload(
        "case-1",
        stage_a,
        stage_b,
        generated_at=datetime(2026, 3, 30, 22, 5, tzinfo=UTC),
    )

    assert report.case_id == "case-1"
    assert "Rear-end collision" in report.accident_summary
    assert report.location_summary.startswith("123 Figueroa St")
    assert len(report.photo_attachments) == 2
    assert report.party_comparison_rows[0].owner_value == "Mingtao Ding"
    assert report.party_comparison_rows[0].other_party_value == "Alex Kim"
    assert [entry.label for entry in report.timeline_entries] == [
        "Accident occurred",
        "Stage A completed",
        "Stage B completed",
        "Accident report generated",
    ]
    assert report.missing_items == []


def test_build_accident_chat_context_exposes_follow_up_items_for_incomplete_case() -> None:
    stage_a = StageAAccidentIntake(
        owner_party=PartyRecord(role=PartyRole.OWNER, name="Mingtao Ding"),
        injuries_reported=True,
        police_called=True,
    )

    report = build_accident_report_payload("case-2", stage_a, None, generated_at=datetime(2026, 3, 30, 23, 0, tzinfo=UTC))
    chat_context = build_accident_chat_context(report)

    assert chat_context.case_id == "case-2"
    assert chat_context.pinned_document_title == "ClaimMate Accident Report - case-2"
    assert any("Location" not in fact for fact in chat_context.key_facts)
    assert "Stage B home follow-up details have not been completed yet." in chat_context.follow_up_items
    assert "Other party information is incomplete." in chat_context.follow_up_items


def test_build_accident_report_payload_uses_none_for_missing_location_summary() -> None:
    stage_a = StageAAccidentIntake(
        owner_party=PartyRecord(role=PartyRole.OWNER, name="Mingtao Ding"),
    )

    report = build_accident_report_payload("case-3", stage_a, None, generated_at=datetime(2026, 3, 31, 1, 0, tzinfo=UTC))

    assert report.location_summary is None

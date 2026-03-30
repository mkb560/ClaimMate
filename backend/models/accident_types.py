from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class AccidentIntakeStage(StrEnum):
    STAGE_A = "stage_a"
    STAGE_B = "stage_b"


class PartyRole(StrEnum):
    OWNER = "owner"
    OTHER_DRIVER = "other_driver"
    WITNESS = "witness"


class PhotoCategory(StrEnum):
    OVERVIEW = "overview"
    OWNER_DAMAGE = "owner_damage"
    OTHER_DAMAGE = "other_damage"
    INTERSECTION = "intersection"
    DOCUMENT = "document"
    OTHER = "other"


@dataclass(slots=True)
class LocationSnapshot:
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    gps_captured_at: datetime | None = None


@dataclass(slots=True)
class VehicleRecord:
    year: int | None = None
    make: str | None = None
    model: str | None = None
    color: str | None = None
    license_plate: str | None = None
    vin: str | None = None


@dataclass(slots=True)
class PartyRecord:
    role: PartyRole
    name: str = ""
    phone: str | None = None
    email: str | None = None
    insurer: str | None = None
    policy_number: str | None = None
    claim_number: str | None = None
    vehicle: VehicleRecord | None = None


@dataclass(slots=True)
class WitnessRecord:
    name: str
    phone: str | None = None
    note: str | None = None


@dataclass(slots=True)
class PhotoAttachment:
    photo_id: str
    category: PhotoCategory
    storage_key: str
    caption: str | None = None
    taken_at: datetime | None = None
    checklist_item: str | None = None


@dataclass(slots=True)
class StageAAccidentIntake:
    occurred_at: datetime | None = None
    location: LocationSnapshot | None = None
    owner_party: PartyRecord | None = None
    other_party: PartyRecord | None = None
    injuries_reported: bool | None = None
    police_called: bool | None = None
    drivable: bool | None = None
    tow_requested: bool | None = None
    quick_summary: str = ""
    photo_attachments: list[PhotoAttachment] = field(default_factory=list)
    stage_completed_at: datetime | None = None


@dataclass(slots=True)
class StageBAccidentIntake:
    detailed_narrative: str = ""
    damage_summary: str | None = None
    weather_conditions: str | None = None
    road_conditions: str | None = None
    witness_contacts: list[WitnessRecord] = field(default_factory=list)
    police_report_number: str | None = None
    adjuster_name: str | None = None
    repair_shop_name: str | None = None
    follow_up_notes: str | None = None
    additional_photos: list[PhotoAttachment] = field(default_factory=list)
    stage_completed_at: datetime | None = None


@dataclass(slots=True)
class TimelineEntry:
    label: str
    timestamp: datetime
    note: str | None = None


@dataclass(slots=True)
class PartyComparisonRow:
    field_label: str
    owner_value: str
    other_party_value: str


@dataclass(slots=True)
class AccidentReportPayload:
    case_id: str
    report_title: str
    generated_at: datetime
    accident_summary: str
    occurrence_time: datetime | None
    location_summary: str
    owner_party: PartyRecord | None
    other_party: PartyRecord | None
    detailed_narrative: str
    damage_summary: str | None
    injuries_reported: bool | None
    police_called: bool | None
    drivable: bool | None
    tow_requested: bool | None
    weather_conditions: str | None
    road_conditions: str | None
    witness_contacts: list[WitnessRecord]
    police_report_number: str | None
    adjuster_name: str | None
    repair_shop_name: str | None
    photo_attachments: list[PhotoAttachment]
    party_comparison_rows: list[PartyComparisonRow]
    timeline_entries: list[TimelineEntry]
    missing_items: list[str]


@dataclass(slots=True)
class AccidentChatContext:
    case_id: str
    pinned_document_title: str
    summary: str
    key_facts: list[str]
    party_comparison_rows: list[PartyComparisonRow]
    follow_up_items: list[str]
    generated_at: datetime

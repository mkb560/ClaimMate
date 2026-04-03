from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

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


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, str):
        raw = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(raw)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    return None


def deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _vehicle_from_dict(data: dict[str, Any] | None) -> VehicleRecord | None:
    if not data:
        return None
    return VehicleRecord(
        year=data.get("year"),
        make=data.get("make"),
        model=data.get("model"),
        color=data.get("color"),
        license_plate=data.get("license_plate"),
        vin=data.get("vin"),
    )


def _party_from_dict(data: dict[str, Any] | None) -> PartyRecord | None:
    if not data:
        return None
    role_raw = data.get("role", PartyRole.OWNER.value)
    role = PartyRole(role_raw) if isinstance(role_raw, str) else role_raw
    return PartyRecord(
        role=role,
        name=data.get("name") or "",
        phone=data.get("phone"),
        email=data.get("email"),
        insurer=data.get("insurer"),
        policy_number=data.get("policy_number"),
        claim_number=data.get("claim_number"),
        vehicle=_vehicle_from_dict(data.get("vehicle")),
    )


def _photo_from_dict(data: dict[str, Any]) -> PhotoAttachment:
    cat_raw = data.get("category", PhotoCategory.OTHER.value)
    category = PhotoCategory(cat_raw) if isinstance(cat_raw, str) else cat_raw
    return PhotoAttachment(
        photo_id=data["photo_id"],
        category=category,
        storage_key=data["storage_key"],
        caption=data.get("caption"),
        taken_at=_parse_dt(data.get("taken_at")),
        checklist_item=data.get("checklist_item"),
    )


def _location_from_dict(data: dict[str, Any] | None) -> LocationSnapshot | None:
    if not data:
        return None
    return LocationSnapshot(
        address=data.get("address"),
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        gps_captured_at=_parse_dt(data.get("gps_captured_at")),
    )


def stage_a_from_dict(data: dict[str, Any]) -> StageAAccidentIntake:
    if not data:
        return StageAAccidentIntake()
    photos = data.get("photo_attachments") or []
    return StageAAccidentIntake(
        occurred_at=_parse_dt(data.get("occurred_at")),
        location=_location_from_dict(data.get("location")),
        owner_party=_party_from_dict(data.get("owner_party")),
        other_party=_party_from_dict(data.get("other_party")),
        injuries_reported=data.get("injuries_reported"),
        police_called=data.get("police_called"),
        drivable=data.get("drivable"),
        tow_requested=data.get("tow_requested"),
        quick_summary=data.get("quick_summary") or "",
        photo_attachments=[_photo_from_dict(p) for p in photos if isinstance(p, dict)],
        stage_completed_at=_parse_dt(data.get("stage_completed_at")),
    )


def _witness_from_dict(data: dict[str, Any]) -> WitnessRecord:
    return WitnessRecord(
        name=data["name"],
        phone=data.get("phone"),
        note=data.get("note"),
    )


def stage_b_from_dict(data: dict[str, Any] | None) -> StageBAccidentIntake | None:
    if not data:
        return None
    witnesses = data.get("witness_contacts") or []
    extras = data.get("additional_photos") or []
    return StageBAccidentIntake(
        detailed_narrative=data.get("detailed_narrative") or "",
        damage_summary=data.get("damage_summary"),
        weather_conditions=data.get("weather_conditions"),
        road_conditions=data.get("road_conditions"),
        witness_contacts=[_witness_from_dict(w) for w in witnesses if isinstance(w, dict)],
        police_report_number=data.get("police_report_number"),
        adjuster_name=data.get("adjuster_name"),
        repair_shop_name=data.get("repair_shop_name"),
        follow_up_notes=data.get("follow_up_notes"),
        additional_photos=[_photo_from_dict(p) for p in extras if isinstance(p, dict)],
        stage_completed_at=_parse_dt(data.get("stage_completed_at")),
    )


def _jsonable(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, StrEnum):
        return obj.value
    if isinstance(obj, datetime):
        return obj.isoformat()
    if is_dataclass(obj):
        return {k: _jsonable(v) for k, v in asdict(obj).items()}
    if isinstance(obj, dict):
        return {k: _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(i) for i in obj]
    return obj


def stage_a_to_dict(stage: StageAAccidentIntake) -> dict[str, Any]:
    return _jsonable(asdict(stage))


def stage_b_to_dict(stage: StageBAccidentIntake) -> dict[str, Any]:
    return _jsonable(asdict(stage))

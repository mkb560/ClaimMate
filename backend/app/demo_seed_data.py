from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from models.ai_types import ChatEventTrigger

DEMO_ACCIDENT_CASE_ID = "demo-accident-2026-04"


def _normalize_now(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(UTC)
    if now.tzinfo is None:
        return now.replace(tzinfo=UTC)
    return now.astimezone(UTC)


def _iso(dt: datetime) -> str:
    return _normalize_now(dt).isoformat().replace("+00:00", "Z")


def build_demo_stage_a_payload(*, now: datetime | None = None) -> dict[str, Any]:
    current = _normalize_now(now)
    occurred_at = current - timedelta(days=2, hours=3, minutes=15)
    completed_at = occurred_at + timedelta(minutes=28)
    return {
        "occurred_at": _iso(occurred_at),
        "location": {
            "address": "1200 S Figueroa St, Los Angeles, CA 90015",
            "latitude": 34.04302,
            "longitude": -118.26723,
            "gps_captured_at": _iso(occurred_at + timedelta(minutes=4)),
        },
        "owner_party": {
            "role": "owner",
            "name": "Mingtao Ding",
            "phone": "213-555-0110",
            "email": "mingtao.demo@example.com",
            "insurer": "Allstate",
            "policy_number": "804 448 188",
            "vehicle": {
                "year": 2024,
                "make": "Hyundai",
                "model": "Elantra",
                "color": "Silver",
                "license_plate": "9ABC123",
                "vin": "KMHLN4DJ8RU107842",
            },
        },
        "other_party": {
            "role": "other_driver",
            "name": "Taylor Brooks",
            "phone": "323-555-0199",
            "email": "taylor.brooks@example.com",
            "insurer": "GEICO",
            "policy_number": "GXC-2219045",
            "claim_number": "CLM-77881",
            "vehicle": {
                "year": 2022,
                "make": "Toyota",
                "model": "RAV4",
                "color": "Blue",
                "license_plate": "8XYZ552",
                "vin": "2T3P1RFV8NW123456",
            },
        },
        "injuries_reported": False,
        "police_called": True,
        "drivable": True,
        "tow_requested": False,
        "quick_summary": (
            "Rear-end collision at a red light near Crypto.com Arena. "
            "My vehicle stayed drivable and both drivers exchanged insurance information."
        ),
        "photo_attachments": [
            {
                "photo_id": "photo-overview-1",
                "category": "overview",
                "storage_key": "demo/accident/photo-overview-1.jpg",
                "caption": "Wide shot of both vehicles in lane",
                "taken_at": _iso(occurred_at + timedelta(minutes=6)),
                "checklist_item": "Take a wide overview photo of the scene",
            },
            {
                "photo_id": "photo-owner-damage-1",
                "category": "owner_damage",
                "storage_key": "demo/accident/photo-owner-damage-1.jpg",
                "caption": "Rear bumper damage on owner vehicle",
                "taken_at": _iso(occurred_at + timedelta(minutes=8)),
                "checklist_item": "Capture close-up damage on your vehicle",
            },
            {
                "photo_id": "photo-other-damage-1",
                "category": "other_damage",
                "storage_key": "demo/accident/photo-other-damage-1.jpg",
                "caption": "Front grille damage on other vehicle",
                "taken_at": _iso(occurred_at + timedelta(minutes=9)),
                "checklist_item": "Capture close-up damage on the other vehicle",
            },
        ],
        "stage_completed_at": _iso(completed_at),
    }


def build_demo_stage_b_payload(*, now: datetime | None = None) -> dict[str, Any]:
    current = _normalize_now(now)
    completed_at = current - timedelta(days=1, hours=18)
    return {
        "detailed_narrative": (
            "I was fully stopped at a red light when the other driver hit my rear bumper. "
            "Traffic was moderate and visibility was clear. We moved to the curb, exchanged insurance cards, "
            "and I called the non-emergency police line because the other driver initially disputed fault."
        ),
        "damage_summary": (
            "Visible damage includes rear bumper cracking, trunk misalignment, and sensor warning lights. "
            "The other vehicle had front grille and hood damage."
        ),
        "weather_conditions": "Clear",
        "road_conditions": "Dry city street, moderate traffic",
        "witness_contacts": [
            {
                "name": "Jordan Lee",
                "phone": "213-555-0142",
                "note": "Was in the car directly behind the other driver and saw the impact.",
            }
        ],
        "police_report_number": "LAPD-2026-0418",
        "adjuster_name": "Alicia Gomez",
        "repair_shop_name": "USC Auto Body Center",
        "follow_up_notes": (
            "Need to confirm whether OEM bumper replacement is covered and whether ADAS recalibration is included."
        ),
        "additional_photos": [
            {
                "photo_id": "photo-document-1",
                "category": "document",
                "storage_key": "demo/accident/photo-document-1.jpg",
                "caption": "Insurance exchange card photo",
                "taken_at": _iso(current - timedelta(days=1, hours=20)),
                "checklist_item": "Photograph exchanged insurance documents",
            }
        ],
        "stage_completed_at": _iso(completed_at),
    }


def build_demo_claim_dates_payload(*, now: datetime | None = None) -> dict[str, Any]:
    current = _normalize_now(now)
    claim_notice_at = current - timedelta(days=13)
    proof_of_claim_at = current - timedelta(days=20)
    return {
        "claim_notice_at": _iso(claim_notice_at),
        "proof_of_claim_at": _iso(proof_of_claim_at),
    }


def build_demo_chat_event_payloads(case_id: str = DEMO_ACCIDENT_CASE_ID) -> dict[str, dict[str, Any]]:
    owner_only = [{"user_id": "owner-1", "role": "owner"}]
    owner_and_adjuster = [
        {"user_id": "owner-1", "role": "owner"},
        {"user_id": "adjuster-1", "role": "adjuster"},
    ]
    return {
        "deadline_stage_1": {
            "case_id": case_id,
            "sender_role": "owner",
            "message_text": "Any update on the claim?",
            "participants": owner_only,
            "invite_sent": False,
            "trigger": ChatEventTrigger.MESSAGE.value,
            "metadata": {"demo_label": "deadline_stage_1"},
        },
        "claim_rule_stage_1": {
            "case_id": case_id,
            "sender_role": "owner",
            "message_text": "@AI What is the 15-day acknowledgment rule for a California claim?",
            "participants": owner_only,
            "invite_sent": False,
            "trigger": ChatEventTrigger.MESSAGE.value,
            "metadata": {"demo_label": "claim_rule_stage_1"},
        },
        "claim_rule_stage_3": {
            "case_id": case_id,
            "sender_role": "owner",
            "message_text": "@AI What is the 15-day acknowledgment rule for a California claim?",
            "participants": owner_and_adjuster,
            "invite_sent": True,
            "trigger": ChatEventTrigger.MESSAGE.value,
            "metadata": {"demo_label": "claim_rule_stage_3"},
        },
        "delay_stage_2": {
            "case_id": case_id,
            "sender_role": "owner",
            "message_text": "The insurer still has no response and the claim is delayed. What should I prepare before I follow up?",
            "participants": owner_only,
            "invite_sent": True,
            "trigger": ChatEventTrigger.MESSAGE.value,
            "metadata": {"demo_label": "delay_stage_2"},
        },
        "amount_stage_3": {
            "case_id": case_id,
            "sender_role": "owner",
            "message_text": "The repair estimate is too low and I think the insurer underpaid me.",
            "participants": owner_and_adjuster,
            "invite_sent": True,
            "trigger": ChatEventTrigger.MESSAGE.value,
            "metadata": {"demo_label": "amount_stage_3"},
        },
    }

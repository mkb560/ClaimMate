from __future__ import annotations

from datetime import UTC, datetime

from app.accident_codec import deep_merge, stage_a_from_dict, stage_a_to_dict
from models.accident_types import PartyRecord, PartyRole, StageAAccidentIntake


def test_deep_merge_nested_dict() -> None:
    base = {"location": {"address": "A", "latitude": 1.0}, "quick_summary": "x"}
    patch = {"location": {"latitude": 2.0}}
    assert deep_merge(base, patch) == {
        "location": {"address": "A", "latitude": 2.0},
        "quick_summary": "x",
    }


def test_stage_a_roundtrip_dict() -> None:
    original = StageAAccidentIntake(
        occurred_at=datetime(2026, 3, 30, 18, 5, tzinfo=UTC),
        owner_party=PartyRecord(role=PartyRole.OWNER, name="Test User"),
        quick_summary="hello",
    )
    back = stage_a_from_dict(stage_a_to_dict(original))
    assert back.quick_summary == original.quick_summary
    assert back.owner_party is not None
    assert back.owner_party.name == "Test User"
    assert back.occurred_at == original.occurred_at

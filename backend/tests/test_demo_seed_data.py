from datetime import UTC, datetime

from app.demo_seed_data import (
    DEMO_ACCIDENT_CASE_ID,
    build_demo_chat_event_payloads,
    build_demo_claim_dates_payload,
    build_demo_stage_a_payload,
    build_demo_stage_b_payload,
)


def test_build_demo_stage_a_payload_includes_required_frontend_fields() -> None:
    payload = build_demo_stage_a_payload(now=datetime(2026, 4, 3, 12, 0, tzinfo=UTC))

    assert payload["owner_party"]["role"] == "owner"
    assert payload["other_party"]["role"] == "other_driver"
    assert payload["location"]["address"]
    assert len(payload["photo_attachments"]) >= 2


def test_build_demo_stage_b_payload_includes_follow_up_details() -> None:
    payload = build_demo_stage_b_payload(now=datetime(2026, 4, 3, 12, 0, tzinfo=UTC))

    assert payload["police_report_number"] == "LAPD-2026-0418"
    assert payload["witness_contacts"][0]["name"] == "Jordan Lee"
    assert payload["adjuster_name"] == "Alicia Gomez"


def test_build_demo_claim_dates_payload_uses_alert_friendly_relative_dates() -> None:
    payload = build_demo_claim_dates_payload(now=datetime(2026, 4, 3, 12, 0, tzinfo=UTC))

    assert payload["claim_notice_at"] == "2026-03-21T12:00:00Z"
    assert payload["proof_of_claim_at"] == "2026-03-14T12:00:00Z"


def test_build_demo_chat_event_payloads_cover_stage_1_and_stage_3() -> None:
    events = build_demo_chat_event_payloads()

    assert set(events) == {
        "deadline_stage_1",
        "claim_rule_stage_1",
        "claim_rule_stage_3",
        "delay_stage_2",
        "amount_stage_3",
    }
    assert events["deadline_stage_1"]["case_id"] == DEMO_ACCIDENT_CASE_ID
    assert events["claim_rule_stage_1"]["participants"] == [{"user_id": "owner-1", "role": "owner"}]
    assert events["delay_stage_2"]["invite_sent"] is True
    assert events["delay_stage_2"]["participants"] == [{"user_id": "owner-1", "role": "owner"}]
    assert events["claim_rule_stage_3"]["invite_sent"] is True
    assert events["claim_rule_stage_3"]["participants"][1]["role"] == "adjuster"
    assert events["amount_stage_3"]["participants"][1]["role"] == "adjuster"

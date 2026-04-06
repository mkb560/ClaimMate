from __future__ import annotations

import pytest

from scripts.run_demo_smoke import (
    SmokePlan,
    _build_chat_message_body,
    _build_seed_policy_body,
    _build_smoke_plan,
    _normalize_base_url,
    _pick_chat_request,
    _pick_demo_policy,
    _validate_case_snapshot,
    _validate_chat_response,
    _validate_chat_messages_growth,
)


def test_normalize_base_url_trims_trailing_slashes() -> None:
    assert _normalize_base_url("https://example.com///") == "https://example.com"


def test_pick_demo_policy_raises_for_unknown_key() -> None:
    with pytest.raises(ValueError):
        _pick_demo_policy([{"policy_key": "allstate-change"}], "missing")


def test_build_smoke_plan_uses_demo_defaults() -> None:
    plan = _build_smoke_plan(
        base_url="https://example.com/",
        catalog=[
            {
                "policy_key": "allstate-change",
                "default_case_id": "allstate-change-2025-05",
                "sample_questions": ["Who are the policyholders?"],
            }
        ],
        policy_key="allstate-change",
        policy_case_id=None,
        ask_question=None,
        accident_case_id="demo-accident-2026-04",
        chat_label="claim_rule_stage_3",
    )

    assert plan == SmokePlan(
        base_url="https://example.com",
        policy_key="allstate-change",
        policy_case_id="allstate-change-2025-05",
        policy_question="Who are the policyholders?",
        accident_case_id="demo-accident-2026-04",
        chat_label="claim_rule_stage_3",
    )


def test_build_seed_policy_body_omits_default_case_id() -> None:
    plan = SmokePlan(
        base_url="https://example.com",
        policy_key="allstate-change",
        policy_case_id="allstate-change-2025-05",
        policy_question="Who are the policyholders?",
        accident_case_id="demo-accident-2026-04",
        chat_label="claim_rule_stage_3",
    )

    body = _build_seed_policy_body(
        plan,
        {
            "policy_key": "allstate-change",
            "default_case_id": "allstate-change-2025-05",
        },
    )

    assert body is None


def test_build_seed_policy_body_uses_policy_key_for_custom_case_id() -> None:
    plan = SmokePlan(
        base_url="https://example.com",
        policy_key="progressive-verification",
        policy_case_id="custom-demo-case",
        policy_question="What is the policy number?",
        accident_case_id="demo-accident-2026-04",
        chat_label="claim_rule_stage_3",
    )

    body = _build_seed_policy_body(
        plan,
        {
            "policy_key": "progressive-verification",
            "default_case_id": "progressive-verification-2026-03",
        },
    )

    assert body == {"policy_key": "progressive-verification"}


def test_pick_chat_request_requires_existing_label() -> None:
    with pytest.raises(ValueError):
        _pick_chat_request({"sample_chat_requests": {"deadline_stage_1": {}}}, "claim_rule_stage_3")


def test_build_chat_message_body_preserves_lou_friendly_fields() -> None:
    body = _build_chat_message_body(
        {
            "message_text": "@AI What is the 15-day acknowledgment rule for a California claim?",
            "sender_role": "owner",
            "invite_sent": True,
            "participants": [{"user_id": "owner-1", "role": "owner"}],
        }
    )

    assert body == {
        "message_text": "@AI What is the 15-day acknowledgment rule for a California claim?",
        "sender_role": "owner",
        "invite_sent": True,
        "participants": [{"user_id": "owner-1", "role": "owner"}],
    }


def test_validate_case_snapshot_requires_room_bootstrap() -> None:
    plan = SmokePlan(
        base_url="https://example.com",
        policy_key="allstate-change",
        policy_case_id="allstate-change-2025-05",
        policy_question="Who are the policyholders?",
        accident_case_id="demo-accident-2026-04",
        chat_label="claim_rule_stage_3",
    )

    with pytest.raises(ValueError):
        _validate_case_snapshot({"case_id": "demo-accident-2026-04", "room_bootstrap": None}, plan)


def test_validate_chat_response_requires_stage_3_prefix() -> None:
    plan = SmokePlan(
        base_url="https://example.com",
        policy_key="allstate-change",
        policy_case_id="allstate-change-2025-05",
        policy_question="Who are the policyholders?",
        accident_case_id="demo-accident-2026-04",
        chat_label="claim_rule_stage_3",
    )

    with pytest.raises(ValueError):
        _validate_chat_response(
            {
                "case_id": "demo-accident-2026-04",
                "response": {"text": "The insurer must acknowledge within 15 days."},
            },
            plan,
        )


def test_validate_chat_messages_growth_checks_trailing_user_and_ai_rows() -> None:
    before_payload = {"messages": [{"id": "old-1", "message_type": "user", "body_text": "older"}]}
    after_payload = {
        "messages": [
            {"id": "old-1", "message_type": "user", "body_text": "older"},
            {
                "id": "new-user",
                "message_type": "user",
                "body_text": "@AI demo question",
                "metadata": {"source": "post_chat_messages"},
            },
            {
                "id": "new-ai",
                "message_type": "ai",
                "body_text": "For reference: demo answer",
                "ai_payload": {"text": "For reference: demo answer"},
            },
        ]
    }

    _validate_chat_messages_growth(
        before_payload=before_payload,
        after_payload=after_payload,
        posted_message_text="@AI demo question",
        ai_response_text="For reference: demo answer",
    )

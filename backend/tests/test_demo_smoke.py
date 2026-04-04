from __future__ import annotations

import pytest

from scripts.run_demo_smoke import (
    SmokePlan,
    _build_seed_policy_body,
    _build_smoke_plan,
    _normalize_base_url,
    _pick_chat_request,
    _pick_demo_policy,
    _validate_chat_response,
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

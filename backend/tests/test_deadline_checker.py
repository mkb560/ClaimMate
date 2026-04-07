from datetime import UTC, datetime, timedelta

from ai.deadline import deadline_checker
from ai.deadline.deadline_checker import (
    DeadlineWindow,
    _cooldown_elapsed,
    _format_deadline_explainer,
    _format_deadline_message,
    _should_alert,
    calculate_deadline_windows,
    is_deadline_question,
)
from ai.rag.prompt_templates import DISCLAIMER_FOOTER
from models.ai_types import ChatStage


def _window(*, days_remaining: int, is_overdue: bool = False) -> DeadlineWindow:
    source_date = datetime(2026, 4, 1, tzinfo=UTC)
    return DeadlineWindow(
        label="acknowledgment",
        source_date_label="claim notice date",
        source_date=source_date,
        due_at=source_date + timedelta(days=15),
        days_remaining=days_remaining,
        is_overdue=is_overdue,
    )


def test_deadline_windows_include_acknowledgment_and_decision() -> None:
    now = datetime(2026, 4, 10, tzinfo=UTC)
    windows = calculate_deadline_windows(
        claim_notice_at=datetime(2026, 4, 1, tzinfo=UTC),
        proof_of_claim_at=datetime(2026, 4, 5, tzinfo=UTC),
        now=now,
    )

    assert len(windows) == 2
    assert windows[0].label == "acknowledgment"
    assert windows[0].days_remaining == 6
    assert windows[1].label == "decision"
    assert windows[1].days_remaining == 35


def test_deadline_windows_mark_overdue_items() -> None:
    now = datetime(2026, 5, 1, tzinfo=UTC)
    windows = calculate_deadline_windows(
        claim_notice_at=datetime(2026, 4, 1, tzinfo=UTC),
        proof_of_claim_at=None,
        now=now,
    )

    assert len(windows) == 1
    assert windows[0].is_overdue is True
    assert windows[0].days_remaining < 0


def test_deadline_message_uses_stage_3_neutral_prefix() -> None:
    message = _format_deadline_message(_window(days_remaining=2), stage=ChatStage.STAGE_3)

    assert message.startswith("For reference: Deadline reminder")
    assert "2026-04-16" in message
    assert DISCLAIMER_FOOTER in message


def test_deadline_message_omits_neutral_prefix_in_stage_1() -> None:
    message = _format_deadline_message(_window(days_remaining=2), stage=ChatStage.STAGE_1)

    assert message.startswith("Deadline reminder")
    assert not message.startswith("For reference:")


def test_deadline_question_detector_matches_common_phrases() -> None:
    assert is_deadline_question("What deadlines should I know?") is True
    assert is_deadline_question("Can you explain the 40-day decision timeline?") is True
    assert is_deadline_question("Should I track the 15-day acknowledgment window?") is True
    assert is_deadline_question("What is the California 15-day claim acknowledgment rule?") is False
    assert is_deadline_question("Does this policy include rental reimbursement?") is False


def test_deadline_explainer_formats_saved_windows_for_stage_1() -> None:
    message = _format_deadline_explainer([_window(days_remaining=2)], stage=ChatStage.STAGE_1)

    assert message.startswith("Deadline overview based on saved case dates")
    assert "- acknowledgment:" in message
    assert "2026-04-16" in message
    assert "due in 2 day(s)" in message
    assert "15-day acknowledgment" in message
    assert DISCLAIMER_FOOTER in message


def test_deadline_explainer_uses_stage_3_neutral_prefix() -> None:
    message = _format_deadline_explainer([_window(days_remaining=0)], stage=ChatStage.STAGE_3)

    assert message.startswith("For reference: Deadline overview")
    assert "due today" in message


def test_deadline_explainer_handles_missing_dates() -> None:
    message = _format_deadline_explainer([], stage=ChatStage.STAGE_1)

    assert message.startswith("Deadline overview: I do not see saved claim dates")
    assert "15-day acknowledgment window" in message
    assert "40-day decision window" in message


def test_deadline_cooldown_elapsed_respects_config(monkeypatch) -> None:
    now = datetime(2026, 4, 10, 12, tzinfo=UTC)
    monkeypatch.setattr(deadline_checker.ai_config, "deadline_alert_cooldown_hours", 24)

    assert _cooldown_elapsed(None, now) is True
    assert _cooldown_elapsed(now - timedelta(hours=23), now) is False
    assert _cooldown_elapsed(now - timedelta(hours=24), now) is True


def test_should_alert_respects_threshold_and_overdue(monkeypatch) -> None:
    monkeypatch.setattr(deadline_checker.ai_config, "deadline_alert_threshold_days", 5)

    assert _should_alert(_window(days_remaining=5)) is True
    assert _should_alert(_window(days_remaining=6)) is False
    assert _should_alert(_window(days_remaining=-1, is_overdue=True)) is True

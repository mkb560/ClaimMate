from datetime import UTC, datetime

from ai.deadline.deadline_checker import calculate_deadline_windows


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


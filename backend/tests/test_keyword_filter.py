from ai.dispute.keyword_filter import detect_dispute_signal


def test_hard_trigger_dispute_signal() -> None:
    signal = detect_dispute_signal("The insurer denied my claim and sent a rejection letter.")
    assert signal.triggered is True
    assert signal.confidence == 0.9
    assert "denied my claim" in signal.matched


def test_soft_trigger_requires_two_matches() -> None:
    signal = detect_dispute_signal("This amount feels too low and the delay is not fair.")
    assert signal.triggered is True
    assert signal.confidence == 0.6


def test_soft_trigger_does_not_fire_with_one_match() -> None:
    signal = detect_dispute_signal("This feels unfair.")
    assert signal.triggered is False


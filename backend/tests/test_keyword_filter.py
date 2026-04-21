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


def test_common_amount_dispute_phrasing_is_a_hard_signal() -> None:
    signal = detect_dispute_signal("I disagree with the repair amount; what should I ask for?")
    assert signal.triggered is True
    assert signal.confidence == 0.9
    assert "disagree with the repair amount" in signal.matched


def test_common_no_response_phrasing_is_a_hard_signal() -> None:
    signal = detect_dispute_signal("The insurer has not responded for two weeks, what should I do?")
    assert signal.triggered is True
    assert signal.confidence == 0.9
    assert "has not responded" in signal.matched


def test_soft_trigger_does_not_fire_with_one_match() -> None:
    signal = detect_dispute_signal("This feels unfair.")
    assert signal.triggered is False

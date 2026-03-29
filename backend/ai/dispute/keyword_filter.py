from __future__ import annotations

from dataclasses import dataclass


HARD_TRIGGERS = (
    "denied my claim",
    "claim denied",
    "bad faith",
    "underpaid",
    "refuse to pay",
    "wrong amount",
    "rejection letter",
)

SOFT_TRIGGERS = (
    "disagree",
    "too low",
    "not fair",
    "no response",
    "delay",
    "ignored",
)


@dataclass(slots=True)
class DisputeSignal:
    triggered: bool
    confidence: float
    matched: list[str]


def detect_dispute_signal(message_text: str) -> DisputeSignal:
    lowered = message_text.lower()

    hard_matches = [trigger for trigger in HARD_TRIGGERS if trigger in lowered]
    if hard_matches:
        return DisputeSignal(triggered=True, confidence=0.9, matched=hard_matches)

    soft_matches = [trigger for trigger in SOFT_TRIGGERS if trigger in lowered]
    if len(soft_matches) >= 2:
        return DisputeSignal(triggered=True, confidence=0.6, matched=soft_matches)

    return DisputeSignal(triggered=False, confidence=0.0, matched=soft_matches)


from __future__ import annotations

import re

MENTION_RE = re.compile(r"@ai\b", re.IGNORECASE)


def contains_ai_mention(message_text: str) -> bool:
    return bool(MENTION_RE.search(message_text))


def extract_ai_question(message_text: str) -> str | None:
    match = MENTION_RE.search(message_text)
    if not match:
        return None
    question = message_text[match.end() :].strip()
    return question or None


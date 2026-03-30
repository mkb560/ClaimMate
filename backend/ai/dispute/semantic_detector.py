from __future__ import annotations

import json
from dataclasses import dataclass

from openai import AsyncOpenAI

from ai.clients import get_openai_client
from ai.config import ai_config

STATUTE_BY_DISPUTE_TYPE = {
    "DENIAL": "10 CCR §2695.7(b)",
    "DELAY": "10 CCR §2695.5(e) / §2695.7(c)",
    "AMOUNT": "10 CCR §2695.8",
    "OTHER": "10 CCR §2695",
    "NOT_DISPUTE": None,
}


@dataclass(slots=True)
class DisputeClassification:
    is_dispute: bool
    dispute_type: str
    recommended_statute: str | None
    rationale: str = ""


async def classify_dispute(
    message_text: str,
    *,
    client: AsyncOpenAI | None = None,
) -> DisputeClassification:
    openai_client = client or get_openai_client()
    response = await openai_client.chat.completions.create(
        model=ai_config.classification_model,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "Classify whether the user's insurance-claim message is a dispute. "
                    "Return JSON with keys: dispute_type, is_dispute, rationale. "
                    "Allowed dispute_type values: DENIAL, DELAY, AMOUNT, OTHER, NOT_DISPUTE."
                ),
            },
            {"role": "user", "content": message_text},
        ],
        max_completion_tokens=150,
    )
    payload = json.loads(response.choices[0].message.content or "{}")
    dispute_type = str(payload.get("dispute_type", "NOT_DISPUTE")).upper()
    if dispute_type not in STATUTE_BY_DISPUTE_TYPE:
        dispute_type = "NOT_DISPUTE"
    is_dispute = bool(payload.get("is_dispute")) and dispute_type != "NOT_DISPUTE"
    return DisputeClassification(
        is_dispute=is_dispute,
        dispute_type=dispute_type,
        recommended_statute=STATUTE_BY_DISPUTE_TYPE[dispute_type],
        rationale=str(payload.get("rationale", "")),
    )

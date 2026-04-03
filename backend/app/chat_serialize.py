from __future__ import annotations

from dataclasses import asdict
from typing import Any

from models.ai_types import AIResponse


def ai_response_to_dict(response: AIResponse) -> dict[str, Any]:
    return {
        "text": response.text,
        "citations": [asdict(c) for c in response.citations],
        "trigger": response.trigger.value,
        "metadata": response.metadata,
    }

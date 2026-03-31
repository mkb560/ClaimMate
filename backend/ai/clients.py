from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from ai.config import get_ai_config


@lru_cache(maxsize=1)
def get_openai_client() -> AsyncOpenAI:
    config = get_ai_config()
    config.require_openai()
    return AsyncOpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
    )

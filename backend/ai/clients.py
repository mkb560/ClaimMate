from __future__ import annotations

import asyncio
import weakref

from openai import AsyncOpenAI

from ai.config import get_ai_config

DEFAULT_OPENAI_TIMEOUT_SECONDS = 60.0
_fallback_client: AsyncOpenAI | None = None
_per_loop_clients: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncOpenAI] = weakref.WeakKeyDictionary()


def _build_client() -> AsyncOpenAI:
    config = get_ai_config()
    config.require_openai()
    return AsyncOpenAI(
        api_key=config.openai_api_key,
        base_url=config.openai_base_url,
        timeout=DEFAULT_OPENAI_TIMEOUT_SECONDS,
    )


def get_openai_client() -> AsyncOpenAI:
    global _fallback_client
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        if _fallback_client is None:
            _fallback_client = _build_client()
        return _fallback_client

    client = _per_loop_clients.get(loop)
    if client is None:
        client = _build_client()
        _per_loop_clients[loop] = client
    return client

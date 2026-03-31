from __future__ import annotations

from collections.abc import Sequence

from openai import AsyncOpenAI

from ai.clients import get_openai_client
from ai.config import ai_config


async def embed_texts(
    texts: Sequence[str],
    *,
    client: AsyncOpenAI | None = None,
    batch_size: int = 32,
) -> list[list[float]]:
    if not texts:
        return []

    openai_client = client or get_openai_client()
    embeddings: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = list(texts[start : start + batch_size])
        request_kwargs = {
            "model": ai_config.embedding_model,
            "input": batch,
        }
        if ai_config.embedding_model.startswith("text-embedding-3"):
            request_kwargs["dimensions"] = ai_config.vector_dimensions
        response = await openai_client.embeddings.create(**request_kwargs)
        embeddings.extend([list(item.embedding) for item in response.data])

    return embeddings

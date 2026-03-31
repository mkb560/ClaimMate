from types import SimpleNamespace

from ai.ingestion import embedder


class _FakeEmbeddingsAPI:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        inputs = kwargs["input"]
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3]) for _ in inputs]
        )


class _FakeClient:
    def __init__(self) -> None:
        self.embeddings = _FakeEmbeddingsAPI()


async def test_embed_texts_uses_large_embedding_model_with_configured_dimensions(monkeypatch) -> None:
    client = _FakeClient()

    monkeypatch.setattr(embedder.ai_config, "embedding_model", "text-embedding-3-large")
    monkeypatch.setattr(embedder.ai_config, "vector_dimensions", 1536)

    vectors = await embedder.embed_texts(["hello world"], client=client)

    assert vectors == [[0.1, 0.2, 0.3]]
    assert client.embeddings.calls == [
        {
            "model": "text-embedding-3-large",
            "input": ["hello world"],
            "dimensions": 1536,
        }
    ]

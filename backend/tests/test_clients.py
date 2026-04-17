import asyncio
import weakref

from ai import clients


class _FakeConfig:
    openai_api_key = "test-key"
    openai_base_url = "https://api.openai.com/v1"

    def require_openai(self) -> None:
        return None


def test_get_openai_client_reuses_client_within_same_loop(monkeypatch) -> None:
    created: list[dict[str, object]] = []

    class _FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            created.append(kwargs)

    monkeypatch.setattr(clients, "get_ai_config", lambda: _FakeConfig())
    monkeypatch.setattr(clients, "AsyncOpenAI", _FakeAsyncOpenAI)
    monkeypatch.setattr(clients, "_fallback_client", None)
    monkeypatch.setattr(clients, "_per_loop_clients", weakref.WeakKeyDictionary())

    async def _get_twice():
        first = clients.get_openai_client()
        second = clients.get_openai_client()
        return first is second

    assert asyncio.run(_get_twice()) is True
    assert len(created) == 1
    assert created[0]["timeout"] == clients.DEFAULT_OPENAI_TIMEOUT_SECONDS


def test_get_openai_client_is_scoped_per_event_loop(monkeypatch) -> None:
    created: list[dict[str, object]] = []

    class _FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            created.append(kwargs)

    monkeypatch.setattr(clients, "get_ai_config", lambda: _FakeConfig())
    monkeypatch.setattr(clients, "AsyncOpenAI", _FakeAsyncOpenAI)
    monkeypatch.setattr(clients, "_fallback_client", None)
    monkeypatch.setattr(clients, "_per_loop_clients", weakref.WeakKeyDictionary())

    async def _get_client():
        return clients.get_openai_client()

    client_one = asyncio.run(_get_client())
    client_two = asyncio.run(_get_client())

    assert client_one is not client_two
    assert len(created) == 2

from ai.ingestion import vector_store


class _FakeScalarResult:
    def all(self):
        return []


class _FakeSession:
    def __init__(self):
        self.statements = []

    async def scalars(self, stmt):
        self.statements.append(str(stmt))
        return _FakeScalarResult()


class _FakeSessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _fake_sessionmaker(session):
    def _make():
        return _FakeSessionContext(session)

    return _make


async def test_list_policy_chunks_uses_stable_page_order(monkeypatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(vector_store, "get_sessionmaker", lambda: _fake_sessionmaker(session))

    await vector_store.list_policy_chunks("demo-case")

    assert session.statements
    assert "ORDER BY" in session.statements[0]
    assert "page_num ASC NULLS LAST" in session.statements[0]


async def test_list_kb_b_chunks_uses_stable_page_order(monkeypatch) -> None:
    session = _FakeSession()
    monkeypatch.setattr(vector_store, "get_sessionmaker", lambda: _fake_sessionmaker(session))

    await vector_store.list_kb_b_chunks()

    assert session.statements
    assert "ORDER BY" in session.statements[0]
    assert "page_num ASC NULLS LAST" in session.statements[0]

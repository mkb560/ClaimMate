from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from models.ai_types import AnswerResponse, Citation


class _DummyEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


def _build_client(monkeypatch, tmp_path: Path) -> TestClient:
    import main

    async def fake_bootstrap(engine) -> None:
        return None

    monkeypatch.setattr(main.ai_config, "database_url", "postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate")
    monkeypatch.setattr(main.ai_config, "openai_api_key", "test-key")
    monkeypatch.setattr("app.paths.LOCAL_POLICY_STORAGE_ROOT", tmp_path)
    monkeypatch.setattr("app.case_service.ensure_case", AsyncMock(return_value=None))
    monkeypatch.setattr(main, "create_ai_engine", lambda: _DummyEngine())
    monkeypatch.setattr(main, "bootstrap_vector_store", fake_bootstrap)
    return TestClient(main.app)


def test_upload_policy_endpoint_indexes_pdf(monkeypatch, tmp_path: Path) -> None:
    from app.routers import policy_ask

    captured: dict[str, object] = {}

    async def fake_ingest_local_policy_file(pdf_path: str | Path, case_id: str) -> int:
        captured["path"] = Path(pdf_path)
        captured["case_id"] = case_id
        return 7

    monkeypatch.setattr(policy_ask, "ingest_local_policy_file", fake_ingest_local_policy_file)

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/cases/demo-case/policy",
            files={"file": ("policy.pdf", b"%PDF-1.4 demo pdf bytes", "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "demo-case",
        "filename": "policy.pdf",
        "chunk_count": 7,
        "status": "indexed",
    }
    assert captured["case_id"] == "demo-case"
    saved_path = captured["path"]
    assert isinstance(saved_path, Path)
    assert saved_path.exists()
    assert saved_path.read_bytes() == b"%PDF-1.4 demo pdf bytes"


def test_ask_endpoint_returns_answer_and_citations(monkeypatch, tmp_path: Path) -> None:
    from app.routers import policy_ask

    async def fake_answer_policy_question(case_id: str, question: str) -> AnswerResponse:
        assert case_id == "demo-case"
        assert question == "Who are the policyholders?"
        return AnswerResponse(
            answer="The policyholders are Anlan Cai and Mingtao Ding. [S1]\n\nDisclaimer: demo",
            citations=[
                Citation(
                    source_type="kb_a",
                    source_label="Your Policy (policy.pdf)",
                    document_id="policy_pdf",
                    page_num=1,
                    section=None,
                    excerpt="Policyholder(s) Anlan Cai Mingtao Ding",
                )
            ],
            disclaimer="Disclaimer: demo",
        )

    monkeypatch.setattr(policy_ask, "answer_policy_question", fake_answer_policy_question)

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/cases/demo-case/ask",
            json={"question": "Who are the policyholders?"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "demo-case",
        "question": "Who are the policyholders?",
        "answer": "The policyholders are Anlan Cai and Mingtao Ding. [S1]\n\nDisclaimer: demo",
        "disclaimer": "Disclaimer: demo",
        "citations": [
            {
                "source_type": "kb_a",
                "source_label": "Your Policy (policy.pdf)",
                "document_id": "policy_pdf",
                "page_num": 1,
                "section": None,
                "excerpt": "Policyholder(s) Anlan Cai Mingtao Ding",
            }
        ],
    }


def test_health_endpoint_reports_ai_ready(monkeypatch, tmp_path: Path) -> None:
    with _build_client(monkeypatch, tmp_path) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["ai_ready"] is True


def test_cors_headers_allow_local_frontend_origin(monkeypatch, tmp_path: Path) -> None:
    with _build_client(monkeypatch, tmp_path) as client:
        response = client.options(
            "/cases/demo-case/ask",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_regex_allows_arbitrary_localhost_port(monkeypatch, tmp_path: Path) -> None:
    with _build_client(monkeypatch, tmp_path) as client:
        response = client.options(
            "/cases/demo-case/ask",
            headers={
                "Origin": "http://localhost:4321",
                "Access-Control-Request-Method": "POST",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4321"

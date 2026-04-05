"""Integration tests against a real Postgres + pgvector instance.

Run from the ``backend`` directory with ``DATABASE_URL`` set (e.g. in ``.env``):

    pytest -m integration -v

These tests do **not** call OpenAI. They exercise the case / accident / claim-dates
APIs and DB bootstrap. For RAG/policy upload against a live DB, you still need
``OPENAI_API_KEY`` and can test manually via the running server or add a separate
marked test later.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ai.config import ai_config

import main


def _database_configured() -> bool:
    return bool(ai_config.database_url and ai_config.database_url.strip())


pytestmark = pytest.mark.integration


@pytest.fixture
def integration_client() -> TestClient:
    if not _database_configured():
        pytest.skip("DATABASE_URL is not set (e.g. copy .env.example to .env and point at your pgvector container).")
    with TestClient(main.app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        err = health.json().get("ai_bootstrap_error")
        if err:
            pytest.skip(f"AI bootstrap failed against DATABASE_URL: {err}")
        yield client


def test_health_db_bootstrap_ok(integration_client: TestClient) -> None:
    r = integration_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["ai_bootstrap_error"] is None


def test_case_and_accident_report_round_trip(integration_client: TestClient) -> None:
    created: str | None = None
    try:
        r = integration_client.post("/cases", json={})
        assert r.status_code == 201
        created = r.json()["case_id"]

        r = integration_client.patch(
            f"/cases/{created}/accident/stage-a",
            json={
                "quick_summary": "Integration test rear-end scenario.",
                "owner_party": {
                    "role": "owner",
                    "name": "Integration User",
                    "phone": "555-0100",
                },
                "injuries_reported": False,
                "police_called": True,
            },
        )
        assert r.status_code == 200
        assert r.json()["stage_a"]["quick_summary"] == "Integration test rear-end scenario."

        r = integration_client.patch(
            f"/cases/{created}/accident/stage-b",
            json={
                "detailed_narrative": "Stopped at a light; other vehicle struck from behind.",
                "damage_summary": "Rear bumper damage.",
            },
        )
        assert r.status_code == 200

        r = integration_client.post(f"/cases/{created}/accident/report")
        assert r.status_code == 200
        body = r.json()
        assert "report_payload" in body
        assert body["report_payload"]["case_id"] == created
        assert "chat_context" in body
        assert body["chat_context"]["case_id"] == created

        r = integration_client.get(f"/cases/{created}/accident/report")
        assert r.status_code == 200
        assert r.json()["report_payload"]["case_id"] == created

        r = integration_client.patch(
            f"/cases/{created}/claim-dates",
            json={
                "claim_notice_at": "2026-03-28T10:00:00Z",
                "proof_of_claim_at": "2026-03-30T10:00:00Z",
            },
        )
        assert r.status_code == 200
        assert r.json()["claim_notice_at"] is not None

        r = integration_client.get(f"/cases/{created}")
        assert r.status_code == 200
        snapshot = r.json()
        assert snapshot["case_id"] == created
        assert snapshot["stage_a"]["quick_summary"] == "Integration test rear-end scenario."
        assert snapshot["stage_b"]["damage_summary"] == "Rear bumper damage."
        assert snapshot["report_payload"]["case_id"] == created
        assert snapshot["chat_context"]["case_id"] == created
        assert snapshot["claim_notice_at"] == "2026-03-28T10:00:00+00:00"
        rb = snapshot.get("room_bootstrap")
        assert rb is not None
        assert rb.get("pinned_document_title") is not None
    finally:
        if created is not None:
            dr = integration_client.delete(f"/cases/{created}")
            assert dr.status_code == 204

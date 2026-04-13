from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from models.ai_types import AIResponse, AITrigger, AnswerResponse, Citation, ChatEventTrigger
from models.case_orm import CaseRow


class _DummyEngine:
    def __init__(self) -> None:
        self.disposed = False

    async def dispose(self) -> None:
        self.disposed = True


def _build_client(monkeypatch, tmp_path: Path) -> TestClient:
    """Build TestClient with stable CORS: regex must allow any localhost port.

    ``CORSMiddleware`` reads config at import time. A local ``.env`` that clears
    ``CORS_ALLOW_ORIGIN_REGEX`` would otherwise make preflight return 400 for e.g.
    ``http://localhost:4321`` (not in the static allow_origins list).
    """
    import importlib

    import ai.config as cfg_mod
    import main as main_mod

    monkeypatch.setenv(
        "CORS_ALLOW_ORIGIN_REGEX",
        r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    )
    cfg_mod.get_ai_config.cache_clear()
    importlib.reload(cfg_mod)
    importlib.reload(main_mod)

    async def fake_bootstrap(engine) -> None:
        return None

    # Reload gives `main` a fresh `ai_config` instance, but router/deps modules keep the
    # pre-reload singleton. Patch every distinct object so ensure_db_ready and /health
    # see DATABASE_URL + OPENAI_API_KEY (otherwise 503 and ai_ready=false).
    from app import deps
    from app.routers import health

    _db_url = "postgresql+psycopg://claimmate:claimmate@localhost:5433/claimmate"
    _api_key = "test-key"
    for _cfg in {id(c): c for c in (deps.ai_config, health.ai_config, main_mod.ai_config)}.values():
        monkeypatch.setattr(_cfg, "database_url", _db_url)
        monkeypatch.setattr(_cfg, "openai_api_key", _api_key)
    monkeypatch.setattr("app.paths.LOCAL_POLICY_STORAGE_ROOT", tmp_path)
    monkeypatch.setattr("app.case_service.ensure_case", AsyncMock(return_value=None))
    monkeypatch.setattr(main_mod, "create_ai_engine", lambda: _DummyEngine())
    monkeypatch.setattr(main_mod, "bootstrap_vector_store", fake_bootstrap)
    return TestClient(main_mod.app)


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


def test_demo_policy_catalog_endpoint_returns_built_in_policies(monkeypatch, tmp_path: Path) -> None:
    from app.routers import policy_ask

    monkeypatch.setattr(
        policy_ask,
        "list_demo_policies",
        lambda: [
            {
                "policy_key": "allstate-change",
                "default_case_id": "allstate-change-2025-05",
                "label": "Allstate policy change packet",
                "filename": "TEMP_PDF_FILE.pdf",
                "sample_questions": ["Who are the policyholders and what is the policy number?"],
            }
        ],
    )

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.get("/demo/policies")

    assert response.status_code == 200
    assert response.json() == {
        "policies": [
            {
                "policy_key": "allstate-change",
                "default_case_id": "allstate-change-2025-05",
                "label": "Allstate policy change packet",
                "filename": "TEMP_PDF_FILE.pdf",
                "sample_questions": ["Who are the policyholders and what is the policy number?"],
            }
        ]
    }


def test_get_policy_status_endpoint_returns_indexed_policy_summary(monkeypatch, tmp_path: Path) -> None:
    from app.routers import policy_ask

    async def fake_get_policy_status(case_id: str):
        assert case_id == "demo-case"
        return {
            "case_id": case_id,
            "has_policy": True,
            "chunk_count": 12,
            "source_label": "Your Policy (TEMP_PDF_FILE.pdf)",
            "filename": "TEMP_PDF_FILE.pdf",
            "demo_policy": {
                "policy_key": "allstate-change",
                "default_case_id": "allstate-change-2025-05",
                "label": "Allstate policy change packet",
                "filename": "TEMP_PDF_FILE.pdf",
                "sample_questions": [
                    "Who are the policyholders and what is the policy number?",
                ],
            },
        }

    monkeypatch.setattr(policy_ask, "get_policy_status", fake_get_policy_status)

    now = datetime.now(UTC)
    fake_policy_case = CaseRow(
        id="demo-case",
        claim_notice_at=None,
        proof_of_claim_at=None,
        last_deadline_alert_at=None,
        stage_a_json={},
        stage_b_json=None,
        report_payload_json=None,
        chat_context_json=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(policy_ask.case_service, "get_case_row", AsyncMock(return_value=fake_policy_case))

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.get("/cases/demo-case/policy")

    assert response.status_code == 200
    assert response.json()["has_policy"] is True
    assert response.json()["demo_policy"]["policy_key"] == "allstate-change"


def test_seed_policy_demo_endpoint_returns_seeded_payload(monkeypatch, tmp_path: Path) -> None:
    from app.routers import policy_ask

    async def fake_seed_demo_policy(case_id: str, policy_key: str | None = None):
        assert case_id == "allstate-change-2025-05"
        assert policy_key is None
        return {
            "case_id": case_id,
            "policy_key": "allstate-change",
            "default_case_id": "allstate-change-2025-05",
            "label": "Allstate policy change packet",
            "filename": "TEMP_PDF_FILE.pdf",
            "chunk_count": 6,
            "status": "indexed",
            "sample_questions": [
                "Who are the policyholders and what is the policy number?",
            ],
        }

    monkeypatch.setattr(policy_ask, "seed_demo_policy", fake_seed_demo_policy)

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post("/cases/allstate-change-2025-05/demo/seed-policy")

    assert response.status_code == 200
    assert response.json()["policy_key"] == "allstate-change"
    assert response.json()["chunk_count"] == 6


def test_seed_policy_demo_endpoint_accepts_policy_key_body(monkeypatch, tmp_path: Path) -> None:
    from app.routers import policy_ask

    async def fake_seed_demo_policy(case_id: str, policy_key: str | None = None):
        assert case_id == "custom-demo-case"
        assert policy_key == "progressive-verification"
        return {
            "case_id": case_id,
            "policy_key": "progressive-verification",
            "default_case_id": "progressive-verification-2026-03",
            "label": "Progressive verification letter",
            "filename": "Verification of Insurance.pdf",
            "chunk_count": 5,
            "status": "indexed",
            "sample_questions": [],
        }

    monkeypatch.setattr(policy_ask, "seed_demo_policy", fake_seed_demo_policy)

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/cases/custom-demo-case/demo/seed-policy",
            json={"policy_key": "progressive-verification"},
        )

    assert response.status_code == 200
    assert response.json()["default_case_id"] == "progressive-verification-2026-03"


def test_seed_policy_demo_endpoint_rejects_unknown_policy_key(monkeypatch, tmp_path: Path) -> None:
    from app.routers import policy_ask

    async def fake_seed_demo_policy(case_id: str, policy_key: str | None = None):
        raise KeyError(policy_key)

    monkeypatch.setattr(policy_ask, "seed_demo_policy", fake_seed_demo_policy)

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/cases/custom-demo-case/demo/seed-policy",
            json={"policy_key": "missing-policy"},
        )

    assert response.status_code == 400
    assert "Unknown policy_key: missing-policy" in response.json()["detail"]
    assert "allstate-change" in response.json()["detail"]


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

    now = datetime.now(UTC)
    fake_ask_case = CaseRow(
        id="demo-case",
        claim_notice_at=None,
        proof_of_claim_at=None,
        last_deadline_alert_at=None,
        stage_a_json={},
        stage_b_json=None,
        report_payload_json=None,
        chat_context_json=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(policy_ask.case_service, "get_case_row", AsyncMock(return_value=fake_ask_case))

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


def test_get_case_snapshot_returns_stored_case_state(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    created_at = datetime(2026, 4, 3, 10, 0, tzinfo=UTC)
    updated_at = datetime(2026, 4, 3, 11, 30, tzinfo=UTC)

    async def fake_get_case_row(case_id: str):
        assert case_id == "demo-case"
        return CaseRow(
            id="demo-case",
            claim_notice_at=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
            proof_of_claim_at=datetime(2026, 3, 25, 12, 0, tzinfo=UTC),
            last_deadline_alert_at=None,
            stage_a_json={"quick_summary": "Rear-end collision.", "drivable": True},
            stage_b_json={"damage_summary": "Rear bumper cracked."},
            report_payload_json={"case_id": "demo-case", "report_title": "ClaimMate Accident Report - demo-case"},
            chat_context_json={"case_id": "demo-case", "pinned_document_title": "ClaimMate Accident Report - demo-case"},
            created_at=created_at,
            updated_at=updated_at,
        )

    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", fake_get_case_row)

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.get("/cases/demo-case")

    assert response.status_code == 200
    assert response.json() == {
        "case_id": "demo-case",
        "claim_notice_at": "2026-03-21T12:00:00+00:00",
        "proof_of_claim_at": "2026-03-25T12:00:00+00:00",
        "last_deadline_alert_at": None,
        "stage_a": {"quick_summary": "Rear-end collision.", "drivable": True},
        "stage_b": {"damage_summary": "Rear bumper cracked."},
        "report_payload": {
            "case_id": "demo-case",
            "report_title": "ClaimMate Accident Report - demo-case",
        },
        "chat_context": {
            "case_id": "demo-case",
            "pinned_document_title": "ClaimMate Accident Report - demo-case",
        },
        "room_bootstrap": {
            "pinned_document_title": "ClaimMate Accident Report - demo-case",
            "summary": None,
            "key_facts": [],
            "follow_up_items": [],
            "party_comparison_rows": [],
            "generated_at": None,
        },
        "created_at": "2026-04-03T10:00:00+00:00",
        "updated_at": "2026-04-03T11:30:00+00:00",
    }


def test_get_case_snapshot_returns_404_for_missing_case(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", AsyncMock(return_value=None))

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.get("/cases/missing-case")

    assert response.status_code == 404
    assert response.json() == {"detail": "Case not found."}


def test_seed_accident_demo_endpoint_returns_seeded_payload(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    async def fake_seed_demo_accident_case(case_id: str):
        assert case_id == "demo-accident-2026-04"
        return {
            "case_id": case_id,
            "kb_b_status": "existing",
            "stage_a": {"quick_summary": "Rear-end collision."},
            "stage_b": {"damage_summary": "Rear bumper damage."},
            "claim_dates": {"claim_notice_at": "2026-03-21T12:00:00Z"},
            "report_payload": {"case_id": case_id, "report_title": "ClaimMate Accident Report - demo-accident-2026-04"},
            "chat_context": {"case_id": case_id, "pinned_document_title": "ClaimMate Accident Report - demo-accident-2026-04"},
            "sample_chat_requests": {},
            "sample_chat_responses": {
                "claim_rule_stage_3": {
                    "text": "For reference: demo",
                    "citations": [],
                    "trigger": "MENTION",
                    "metadata": {"stage": "stage_3"},
                }
            },
            "sample_chat_errors": {},
            "case_snapshot": {"case_id": case_id},
        }

    monkeypatch.setattr(cases_and_accident, "seed_demo_accident_case", fake_seed_demo_accident_case)

    # Seed-accident must not require a pre-existing row; ensure_case happens inside the service.
    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", AsyncMock(return_value=None))

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post("/cases/demo-accident-2026-04/demo/seed-accident")

    assert response.status_code == 200
    assert response.json()["case_id"] == "demo-accident-2026-04"
    assert response.json()["sample_chat_responses"]["claim_rule_stage_3"]["trigger"] == "MENTION"


def test_chat_event_persists_user_and_ai_when_model_responds(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    now = datetime.now(UTC)
    fake_row = CaseRow(
        id="demo-case",
        claim_notice_at=None,
        proof_of_claim_at=None,
        last_deadline_alert_at=None,
        stage_a_json={},
        stage_b_json=None,
        report_payload_json=None,
        chat_context_json=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", AsyncMock(return_value=fake_row))
    append_user = AsyncMock()
    append_ai = AsyncMock()
    monkeypatch.setattr(cases_and_accident.case_service, "append_chat_user_message", append_user)
    monkeypatch.setattr(cases_and_accident.case_service, "append_chat_ai_message", append_ai)

    async def fake_handle(event):
        assert event.case_id == "demo-case"
        return AIResponse(text="Answer", citations=[], trigger=AITrigger.MENTION, metadata={})

    from app import chat_dispatch

    monkeypatch.setattr(chat_dispatch, "handle_chat_event", fake_handle)

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/cases/demo-case/chat/event",
            json={
                "sender_role": "owner",
                "message_text": "@AI What is the deductible?",
                "participants": [{"user_id": "o1", "role": "owner"}],
                "invite_sent": False,
                "trigger": ChatEventTrigger.MESSAGE.value,
                "metadata": {},
            },
        )

    assert response.status_code == 200
    append_user.assert_awaited_once()
    append_ai.assert_awaited_once()
    assert response.json()["response"]["text"] == "Answer"


def test_chat_event_skips_ai_append_when_no_response(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    now = datetime.now(UTC)
    fake_row = CaseRow(
        id="demo-case",
        claim_notice_at=None,
        proof_of_claim_at=None,
        last_deadline_alert_at=None,
        stage_a_json={},
        stage_b_json=None,
        report_payload_json=None,
        chat_context_json=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", AsyncMock(return_value=fake_row))
    append_user = AsyncMock()
    append_ai = AsyncMock()
    monkeypatch.setattr(cases_and_accident.case_service, "append_chat_user_message", append_user)
    monkeypatch.setattr(cases_and_accident.case_service, "append_chat_ai_message", append_ai)
    from app import chat_dispatch

    monkeypatch.setattr(chat_dispatch, "handle_chat_event", AsyncMock(return_value=None))

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/cases/demo-case/chat/event",
            json={
                "sender_role": "owner",
                "message_text": "No AI mention here",
                "participants": [{"user_id": "o1", "role": "owner"}],
                "invite_sent": False,
                "trigger": ChatEventTrigger.MESSAGE.value,
                "metadata": {},
            },
        )

    assert response.status_code == 200
    append_user.assert_awaited_once()
    append_ai.assert_not_called()
    assert response.json()["response"] is None


def test_get_chat_messages_returns_list(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    now = datetime.now(UTC)
    fake_row = CaseRow(
        id="demo-case",
        claim_notice_at=None,
        proof_of_claim_at=None,
        last_deadline_alert_at=None,
        stage_a_json={},
        stage_b_json=None,
        report_payload_json=None,
        chat_context_json=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", AsyncMock(return_value=fake_row))
    monkeypatch.setattr(
        cases_and_accident.case_service,
        "list_chat_messages",
        AsyncMock(return_value=[{"id": "m1", "message_type": "user", "body_text": "hi"}]),
    )

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.get("/cases/demo-case/chat/messages")

    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == "demo-case"
    assert body["messages"][0]["body_text"] == "hi"


def test_post_chat_messages_triggers_dispatch(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    now = datetime.now(UTC)
    fake_row = CaseRow(
        id="demo-case",
        claim_notice_at=None,
        proof_of_claim_at=None,
        last_deadline_alert_at=None,
        stage_a_json={},
        stage_b_json=None,
        report_payload_json=None,
        chat_context_json=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", AsyncMock(return_value=fake_row))
    monkeypatch.setattr(cases_and_accident.case_service, "append_chat_user_message", AsyncMock())
    monkeypatch.setattr(cases_and_accident.case_service, "append_chat_ai_message", AsyncMock())
    from app import chat_dispatch

    monkeypatch.setattr(
        chat_dispatch,
        "handle_chat_event",
        AsyncMock(return_value=AIResponse(text="Simple", citations=[], trigger=AITrigger.MENTION, metadata={})),
    )

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.post(
            "/cases/demo-case/chat/messages",
            json={"message_text": "@AI test"},
        )

    assert response.status_code == 200
    assert response.json()["response"]["text"] == "Simple"


def test_delete_case_returns_204(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    now = datetime.now(UTC)
    fake_row = CaseRow(
        id="demo-case",
        claim_notice_at=None,
        proof_of_claim_at=None,
        last_deadline_alert_at=None,
        stage_a_json={},
        stage_b_json=None,
        report_payload_json=None,
        chat_context_json=None,
        created_at=now,
        updated_at=now,
    )
    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", AsyncMock(return_value=fake_row))
    monkeypatch.setattr(cases_and_accident.case_service, "delete_case_and_related_data", AsyncMock(return_value=True))

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.delete("/cases/demo-case")

    assert response.status_code == 204


def test_delete_case_missing_returns_404(monkeypatch, tmp_path: Path) -> None:
    from app.routers import cases_and_accident

    monkeypatch.setattr(cases_and_accident.case_service, "get_case_row", AsyncMock(return_value=None))
    monkeypatch.setattr(cases_and_accident.case_service, "delete_case_and_related_data", AsyncMock(return_value=False))

    with _build_client(monkeypatch, tmp_path) as client:
        response = client.delete("/cases/missing-case")

    assert response.status_code == 404


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

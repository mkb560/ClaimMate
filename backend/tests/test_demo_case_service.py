from datetime import UTC, datetime

from models.case_orm import CaseRow


async def test_seed_demo_accident_case_returns_snapshot_and_chat_samples(monkeypatch) -> None:
    from app import demo_case_service

    async def fake_ensure_demo_kb_b_ready(*, allow_index: bool = True) -> str:
        assert allow_index is True
        return "existing"

    async def fake_ensure_case(case_id: str) -> None:
        assert case_id == "demo-accident-2026-04"

    async def fake_patch_stage_a(case_id: str, payload: dict):
        assert case_id == "demo-accident-2026-04"
        return payload

    async def fake_patch_stage_b(case_id: str, payload: dict):
        assert case_id == "demo-accident-2026-04"
        return payload

    async def fake_update_claim_dates(case_id: str, *, claim_notice_at, proof_of_claim_at) -> None:
        assert case_id == "demo-accident-2026-04"
        assert claim_notice_at is not None
        assert proof_of_claim_at is not None

    async def fake_generate_and_store_report(case_id: str):
        assert case_id == "demo-accident-2026-04"
        return (
            {"case_id": case_id, "report_title": "ClaimMate Accident Report - demo-accident-2026-04"},
            {"case_id": case_id, "pinned_document_title": "ClaimMate Accident Report - demo-accident-2026-04"},
        )

    async def fake_handle_chat_event(event):
        return type(
            "_Response",
            (),
            {
                "text": "For reference: demo chat answer",
                "citations": [],
                "trigger": type("_Trigger", (), {"value": "MENTION"})(),
                "metadata": {"stage": "stage_3"},
            },
        )()

    async def fake_get_case_row(case_id: str):
        return CaseRow(
            id=case_id,
            claim_notice_at=datetime(2026, 3, 21, 12, 0, tzinfo=UTC),
            proof_of_claim_at=datetime(2026, 3, 14, 12, 0, tzinfo=UTC),
            last_deadline_alert_at=None,
            stage_a_json={"quick_summary": "Rear-end collision."},
            stage_b_json={"damage_summary": "Rear bumper damage."},
            report_payload_json={"case_id": case_id, "report_title": "ClaimMate Accident Report - demo-accident-2026-04"},
            chat_context_json={"case_id": case_id, "pinned_document_title": "ClaimMate Accident Report - demo-accident-2026-04"},
            created_at=datetime(2026, 4, 4, 10, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 4, 10, 30, tzinfo=UTC),
        )

    monkeypatch.setattr(demo_case_service, "ensure_demo_kb_b_ready", fake_ensure_demo_kb_b_ready)
    monkeypatch.setattr(demo_case_service.case_service, "ensure_case", fake_ensure_case)
    monkeypatch.setattr(demo_case_service.case_service, "patch_stage_a", fake_patch_stage_a)
    monkeypatch.setattr(demo_case_service.case_service, "patch_stage_b", fake_patch_stage_b)
    monkeypatch.setattr(demo_case_service.case_service, "update_claim_dates", fake_update_claim_dates)
    monkeypatch.setattr(demo_case_service.case_service, "generate_and_store_report", fake_generate_and_store_report)
    monkeypatch.setattr(demo_case_service.case_service, "get_case_row", fake_get_case_row)
    monkeypatch.setattr(demo_case_service, "handle_chat_event", fake_handle_chat_event)

    result = await demo_case_service.seed_demo_accident_case()

    assert result["case_id"] == "demo-accident-2026-04"
    assert result["kb_b_status"] == "existing"
    assert result["report_payload"]["case_id"] == "demo-accident-2026-04"
    assert result["chat_context"]["case_id"] == "demo-accident-2026-04"
    assert "claim_rule_stage_3" in result["sample_chat_requests"]
    assert result["sample_chat_responses"]["claim_rule_stage_3"]["text"] == "For reference: demo chat answer"
    assert result["sample_chat_errors"] == {}
    assert result["case_snapshot"]["case_id"] == "demo-accident-2026-04"


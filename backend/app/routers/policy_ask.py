from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from ai.ingestion.ingest_policy import ingest_local_policy_file
from ai.rag.query_engine import answer_policy_question
from app.auth_deps import AuthContext, get_auth_context
from app.case_access import assert_can_access_case
from app.case_validation import validate_case_id
from app.demo_policy_service import get_policy_status, list_demo_policies, list_demo_policy_keys, seed_demo_policy
from app.deps import ensure_ai_ready, ensure_db_ready
from app.paths import LOCAL_POLICY_STORAGE_ROOT
from app.policy_upload import save_uploaded_policy
from app import case_service

router = APIRouter(tags=["policy"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class SeedPolicyBody(BaseModel):
    policy_key: str | None = Field(default=None, max_length=64)


@router.get("/demo/policies")
async def get_demo_policy_catalog() -> dict[str, object]:
    return {"policies": list_demo_policies()}


@router.get("/cases/{case_id}/policy")
async def get_case_policy_status(
    case_id: str,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    ensure_db_ready(request)
    normalized_case_id = validate_case_id(case_id)
    row = await case_service.get_case_row(normalized_case_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    await assert_can_access_case(normalized_case_id, ctx)
    return await get_policy_status(normalized_case_id)


@router.post("/cases/{case_id}/policy")
async def upload_policy(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    normalized_case_id = validate_case_id(case_id)
    ensure_ai_ready(request)
    await assert_can_access_case(normalized_case_id, ctx)
    await case_service.ensure_case(normalized_case_id)
    saved_path = await save_uploaded_policy(normalized_case_id, file, LOCAL_POLICY_STORAGE_ROOT)
    chunk_count = await ingest_local_policy_file(saved_path, case_id=normalized_case_id)
    return {
        "case_id": normalized_case_id,
        "filename": saved_path.name,
        "chunk_count": chunk_count,
        "status": "indexed",
    }


@router.post("/cases/{case_id}/demo/seed-policy")
async def seed_demo_policy_for_case(
    case_id: str,
    request: Request,
    body: SeedPolicyBody | None = None,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    normalized_case_id = validate_case_id(case_id)
    ensure_ai_ready(request)
    await assert_can_access_case(normalized_case_id, ctx)
    await case_service.ensure_case(normalized_case_id)
    seed_request = body or SeedPolicyBody()
    try:
        return await seed_demo_policy(normalized_case_id, seed_request.policy_key)
    except KeyError as exc:
        available = ", ".join(list_demo_policy_keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown policy_key: {exc.args[0]}. Available policy keys: {available}",
        ) from exc
    except LookupError as exc:
        available = ", ".join(list_demo_policy_keys())
        raise HTTPException(
            status_code=400,
            detail=(
                "No default demo policy matches this case_id. "
                f"Provide policy_key in the request body. Available policy keys: {available}"
            ),
        ) from exc


@router.post("/cases/{case_id}/ask")
async def ask_case_question(
    case_id: str,
    payload: AskRequest,
    request: Request,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, object]:
    normalized_case_id = validate_case_id(case_id)
    ensure_ai_ready(request)
    await assert_can_access_case(normalized_case_id, ctx)
    await case_service.ensure_case(normalized_case_id)

    question = payload.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="question must not be empty.")

    answer = await answer_policy_question(normalized_case_id, question)
    return {
        "case_id": normalized_case_id,
        "question": question,
        "answer": answer.answer,
        "disclaimer": answer.disclaimer,
        "citations": [asdict(citation) for citation in answer.citations],
    }

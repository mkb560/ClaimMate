from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from ai.ingestion.ingest_policy import ingest_local_policy_file
from ai.rag.query_engine import answer_policy_question
from app.case_validation import validate_case_id
from app.demo_policy_service import list_demo_policy_keys, seed_demo_policy
from app.deps import ensure_ai_ready
from app.paths import LOCAL_POLICY_STORAGE_ROOT
from app.policy_upload import save_uploaded_policy
from app import case_service

router = APIRouter(tags=["policy"])


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class SeedPolicyBody(BaseModel):
    policy_key: str | None = Field(default=None, max_length=64)


@router.post("/cases/{case_id}/policy")
async def upload_policy(case_id: str, request: Request, file: UploadFile = File(...)) -> dict[str, object]:
    normalized_case_id = validate_case_id(case_id)
    ensure_ai_ready(request)
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
) -> dict[str, object]:
    normalized_case_id = validate_case_id(case_id)
    ensure_ai_ready(request)
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
async def ask_case_question(case_id: str, payload: AskRequest, request: Request) -> dict[str, object]:
    normalized_case_id = validate_case_id(case_id)
    ensure_ai_ready(request)
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

from __future__ import annotations

import re
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ai.config import ai_config
from ai.ingestion.ingest_policy import ingest_local_policy_file
from ai.rag.query_engine import answer_policy_question
from ai.runtime import bootstrap_vector_store, create_ai_engine

BACKEND_ROOT = Path(__file__).resolve().parent
LOCAL_POLICY_STORAGE_ROOT = BACKEND_ROOT / ".local_data" / "policies"
CASE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


def _validate_case_id(case_id: str) -> str:
    if not CASE_ID_RE.fullmatch(case_id):
        raise HTTPException(
            status_code=400,
            detail="case_id may contain only letters, numbers, underscores, and hyphens.",
        )
    return case_id


def _sanitize_filename(filename: str | None) -> str:
    original = Path(filename or "policy.pdf").name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "-", original).strip("-.") or "policy.pdf"
    if not cleaned.lower().endswith(".pdf"):
        cleaned += ".pdf"
    return cleaned


def _ensure_ai_ready(request: Request) -> None:
    if not ai_config.database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured.")
    if not ai_config.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")
    if bootstrap_error := getattr(request.app.state, "ai_bootstrap_error", None):
        raise HTTPException(status_code=503, detail=f"AI bootstrap failed: {bootstrap_error}")


async def _save_uploaded_policy(case_id: str, upload: UploadFile) -> Path:
    if upload.content_type not in {None, "", "application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    filename = _sanitize_filename(upload.filename)
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF uploads are supported.")

    content = await upload.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if not content.startswith(b"%PDF"):
        raise HTTPException(status_code=400, detail="Uploaded file does not look like a PDF.")

    case_dir = LOCAL_POLICY_STORAGE_ROOT / case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    destination = case_dir / filename
    destination.write_bytes(content)
    return destination


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ai_engine = None
    app.state.ai_bootstrap_error = None

    if ai_config.database_url:
        engine = create_ai_engine()
        try:
            await bootstrap_vector_store(engine)
            app.state.ai_engine = engine
        except Exception as exc:  # pragma: no cover - exercised via request-time checks
            app.state.ai_bootstrap_error = str(exc)
            await engine.dispose()

    yield

    engine = getattr(app.state, "ai_engine", None)
    if engine is not None:
        await engine.dispose()


app = FastAPI(title="ClaimMate Backend", version="0.1.0", lifespan=lifespan)

cors_origins = ai_config.cors_allow_origins_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck(request: Request) -> dict[str, object]:
    return {
        "status": "ok",
        "ai_ready": bool(ai_config.database_url and ai_config.openai_api_key and not request.app.state.ai_bootstrap_error),
        "ai_bootstrap_error": request.app.state.ai_bootstrap_error,
    }


@app.post("/cases/{case_id}/policy")
async def upload_policy(case_id: str, request: Request, file: UploadFile = File(...)) -> dict[str, object]:
    normalized_case_id = _validate_case_id(case_id)
    _ensure_ai_ready(request)
    saved_path = await _save_uploaded_policy(normalized_case_id, file)
    chunk_count = await ingest_local_policy_file(saved_path, case_id=normalized_case_id)
    return {
        "case_id": normalized_case_id,
        "filename": saved_path.name,
        "chunk_count": chunk_count,
        "status": "indexed",
    }


@app.post("/cases/{case_id}/ask")
async def ask_case_question(case_id: str, payload: AskRequest, request: Request) -> dict[str, object]:
    normalized_case_id = _validate_case_id(case_id)
    _ensure_ai_ready(request)

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

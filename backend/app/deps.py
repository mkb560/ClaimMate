from __future__ import annotations

from fastapi import HTTPException, Request

from ai.config import ai_config


def ensure_db_ready(request: Request) -> None:
    if not ai_config.database_url:
        raise HTTPException(status_code=503, detail="DATABASE_URL is not configured.")
    if bootstrap_error := getattr(request.app.state, "ai_bootstrap_error", None):
        raise HTTPException(status_code=503, detail=f"AI bootstrap failed: {bootstrap_error}")


def ensure_ai_ready(request: Request) -> None:
    ensure_db_ready(request)
    if not ai_config.openai_api_key:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY is not configured.")

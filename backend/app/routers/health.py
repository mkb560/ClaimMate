from __future__ import annotations

from fastapi import APIRouter, Request

from ai.config import ai_config

router = APIRouter(tags=["health"])


@router.get("/health")
async def healthcheck(request: Request) -> dict[str, object]:
    return {
        "status": "ok",
        "ai_ready": bool(
            ai_config.database_url and ai_config.openai_api_key and not request.app.state.ai_bootstrap_error
        ),
        "ai_bootstrap_error": request.app.state.ai_bootstrap_error,
        "auth_mode": ai_config.auth_mode,
        "policy_storage_ready": getattr(request.app.state, "policy_storage_ready", None),
        "policy_storage_error": getattr(request.app.state, "policy_storage_error", None),
    }

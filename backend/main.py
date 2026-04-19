from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.config import ai_config
from ai.runtime import bootstrap_vector_store, create_ai_engine
from app.logging_utils import configure_logging, log_structured
from app.routers import auth, cases_and_accident, health, invites, policy_ask, ws_chat
from app.storage_runtime import ensure_policy_storage_ready


configure_logging(level_name=ai_config.app_log_level, json_logs=ai_config.app_log_json)
logger = logging.getLogger("claimmate.backend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.ai_engine = None
    app.state.ai_bootstrap_error = None
    storage_ready, storage_error, storage_root = ensure_policy_storage_ready()
    app.state.policy_storage_ready = storage_ready
    app.state.policy_storage_error = storage_error

    log_structured(
        logger,
        logging.INFO,
        "application_startup",
        auth_mode=ai_config.auth_mode,
        storage_root=str(storage_root),
        policy_storage_ready=storage_ready,
        policy_storage_error=storage_error,
        database_configured=bool(ai_config.database_url),
        openai_configured=bool(ai_config.openai_api_key),
    )

    if ai_config.database_url:
        engine = create_ai_engine()
        try:
            await bootstrap_vector_store(engine)
            app.state.ai_engine = engine
            log_structured(logger, logging.INFO, "ai_bootstrap_succeeded")
        except Exception as exc:  # pragma: no cover - exercised via request-time checks
            app.state.ai_bootstrap_error = str(exc)
            log_structured(logger, logging.ERROR, "ai_bootstrap_failed", error=str(exc))
            await engine.dispose()

    yield

    engine = getattr(app.state, "ai_engine", None)
    if engine is not None:
        await engine.dispose()
    log_structured(logger, logging.INFO, "application_shutdown")


app = FastAPI(title="ClaimMate Backend", version="0.1.0", lifespan=lifespan)

cors_origins = ai_config.cors_allow_origins_list()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=ai_config.cors_allow_origin_regex_value(),
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(invites.router)
app.include_router(policy_ask.router)
app.include_router(cases_and_accident.router)
app.include_router(ws_chat.router)


@app.middleware("http")
async def request_logging_middleware(request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        log_structured(
            logger,
            logging.ERROR,
            "http_request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            query=str(request.url.query),
            duration_ms=duration_ms,
        )
        raise

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    log_structured(
        logger,
        logging.INFO,
        "http_request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        query=str(request.url.query),
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    return response

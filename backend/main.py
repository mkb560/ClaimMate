from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai.config import ai_config
from ai.runtime import bootstrap_vector_store, create_ai_engine
from app.routers import cases_and_accident, health, policy_ask


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
    allow_origin_regex=ai_config.cors_allow_origin_regex_value(),
    allow_credentials="*" not in cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(policy_ask.router)
app.include_router(cases_and_accident.router)

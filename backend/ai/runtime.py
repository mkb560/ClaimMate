from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ai.config import ai_config
from ai.ingestion.vector_store import ensure_vector_schema, init_engine
from models import auth_orm  # noqa: F401  # registers auth tables on CaseBase.metadata
from models.case_orm import CaseBase


def create_ai_engine(*, echo: bool = False) -> AsyncEngine:
    ai_config.require_database()
    return create_async_engine(ai_config.database_url, echo=echo)


async def bootstrap_vector_store(engine: AsyncEngine) -> None:
    init_engine(engine)
    await ensure_vector_schema(engine)
    async with engine.begin() as conn:
        await conn.run_sync(CaseBase.metadata.create_all)

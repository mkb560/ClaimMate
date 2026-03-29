from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import JSON, String, Text, delete, select, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from ai.config import ai_config
from ai.ingestion.types import EmbeddedChunk, SourceType


class VectorBase(DeclarativeBase):
    pass


class VectorDocument(VectorBase):
    __tablename__ = ai_config.vector_table_name

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(String(8), nullable=False)
    document_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_num: Mapped[int | None] = mapped_column(nullable=True)
    section: Mapped[str | None] = mapped_column(String(256), nullable=True)
    embedding: Mapped[list[float]] = mapped_column(VECTOR(ai_config.vector_dimensions), nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON().with_variant(JSONB, "postgresql"))


@dataclass(slots=True)
class RetrievedChunk:
    source_type: str
    chunk_text: str
    document_id: str | None
    page_num: int | None
    section: str | None
    metadata: dict[str, Any] = field(default_factory=dict)


_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def init_engine(engine: AsyncEngine) -> None:
    global _sessionmaker
    _sessionmaker = async_sessionmaker(engine, expire_on_commit=False)


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    if _sessionmaker is None:
        raise RuntimeError("init_engine(engine) must be called before vector store operations.")
    return _sessionmaker


async def ensure_vector_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(VectorBase.metadata.create_all)


def _chunks_to_models(chunks: Sequence[EmbeddedChunk]) -> list[VectorDocument]:
    return [
        VectorDocument(
            case_id=chunk.case_id,
            source_type=chunk.source_type.value,
            document_id=chunk.document_id,
            chunk_text=chunk.chunk_text,
            page_num=chunk.page_num,
            section=chunk.section,
            embedding=chunk.embedding,
            metadata_json=chunk.metadata,
        )
        for chunk in chunks
    ]


async def replace_case_chunks(case_id: str, chunks: Sequence[EmbeddedChunk]) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            delete(VectorDocument).where(
                VectorDocument.case_id == case_id,
                VectorDocument.source_type == SourceType.KB_A.value,
            )
        )
        if chunks:
            session.add_all(_chunks_to_models(chunks))
        await session.commit()


async def replace_kb_b_document(document_id: str, chunks: Sequence[EmbeddedChunk]) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            delete(VectorDocument).where(
                VectorDocument.document_id == document_id,
                VectorDocument.source_type == SourceType.KB_B.value,
            )
        )
        if chunks:
            session.add_all(_chunks_to_models(chunks))
        await session.commit()


def _to_retrieved_chunks(records: Iterable[VectorDocument]) -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            source_type=record.source_type,
            chunk_text=record.chunk_text,
            document_id=record.document_id,
            page_num=record.page_num,
            section=record.section,
            metadata=record.metadata_json or {},
        )
        for record in records
    ]


async def search_case_chunks(case_id: str, query_embedding: list[float], top_k: int | None = None) -> list[RetrievedChunk]:
    sessionmaker = get_sessionmaker()
    limit = top_k or ai_config.rag_top_k_per_source
    async with sessionmaker() as session:
        stmt = (
            select(VectorDocument)
            .where(
                VectorDocument.source_type == SourceType.KB_A.value,
                VectorDocument.case_id == case_id,
            )
            .order_by(VectorDocument.embedding.cosine_distance(query_embedding))
            .limit(limit)
        )
        result = await session.scalars(stmt)
        return _to_retrieved_chunks(result.all())


async def search_kb_b_chunks(
    query_embedding: list[float],
    *,
    top_k: int | None = None,
    document_ids: Sequence[str] | None = None,
) -> list[RetrievedChunk]:
    sessionmaker = get_sessionmaker()
    limit = top_k or ai_config.rag_top_k_per_source
    async with sessionmaker() as session:
        stmt = select(VectorDocument).where(VectorDocument.source_type == SourceType.KB_B.value)
        if document_ids:
            stmt = stmt.where(VectorDocument.document_id.in_(list(document_ids)))
        stmt = stmt.order_by(VectorDocument.embedding.cosine_distance(query_embedding)).limit(limit)
        result = await session.scalars(stmt)
        return _to_retrieved_chunks(result.all())


async def list_policy_chunks(case_id: str, *, limit: int = 3) -> list[RetrievedChunk]:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        stmt = (
            select(VectorDocument)
            .where(
                VectorDocument.source_type == SourceType.KB_A.value,
                VectorDocument.case_id == case_id,
            )
            .limit(limit)
        )
        result = await session.scalars(stmt)
        return _to_retrieved_chunks(result.all())

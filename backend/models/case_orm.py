from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class CaseBase(DeclarativeBase):
    pass


class CaseRow(CaseBase):
    """App-layer case record; `id` matches `case_id` string used by RAG and vector_documents."""

    __tablename__ = "cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    claim_notice_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proof_of_claim_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_deadline_alert_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    stage_a_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    stage_b_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    report_payload_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    chat_context_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CaseChatMessageRow(CaseBase):
    """Append-only chat lines for a case (demo / product-lite persistence)."""

    __tablename__ = "case_chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sender_role: Mapped[str] = mapped_column(String(32), nullable=False)
    message_type: Mapped[str] = mapped_column(String(16), nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def generate_case_id() -> str:
    return f"case-{uuid.uuid4().hex[:12]}"

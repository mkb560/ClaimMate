from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, text
from sqlalchemy.dialects.postgresql import JSONB
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


def generate_case_id() -> str:
    return f"case-{uuid.uuid4().hex[:12]}"

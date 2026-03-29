from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from ai.config import ai_config
from ai.ingestion.vector_store import get_sessionmaker
from ai.rag.prompt_templates import DISCLAIMER_FOOTER
from models.ai_types import AIResponse, AITrigger, ChatStage

ACKNOWLEDGMENT_WINDOW_DAYS = 15
DECISION_WINDOW_DAYS = 40

# Integration contract:
# The application layer owns the `cases` table and must provide the following columns:
# - claim_notice_at TIMESTAMPTZ NULL
# - proof_of_claim_at TIMESTAMPTZ NULL
# - last_deadline_alert_at TIMESTAMPTZ NULL
# This module intentionally uses raw SQL so it can integrate before a shared Case ORM model exists.


@dataclass(slots=True)
class DeadlineWindow:
    label: str
    source_date_label: str
    source_date: datetime
    due_at: datetime
    days_remaining: int
    is_overdue: bool


def _normalize_dt(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_window(label: str, source_date_label: str, source_date: datetime, offset_days: int, now: datetime) -> DeadlineWindow:
    due_at = source_date + timedelta(days=offset_days)
    delta = due_at.date() - now.date()
    return DeadlineWindow(
        label=label,
        source_date_label=source_date_label,
        source_date=source_date,
        due_at=due_at,
        days_remaining=delta.days,
        is_overdue=delta.days < 0,
    )


def calculate_deadline_windows(
    *,
    claim_notice_at: datetime | None,
    proof_of_claim_at: datetime | None,
    now: datetime | None = None,
) -> list[DeadlineWindow]:
    current_time = _normalize_dt(now) or datetime.now(UTC)
    windows: list[DeadlineWindow] = []

    if claim_notice_at := _normalize_dt(claim_notice_at):
        windows.append(
            _build_window(
                "acknowledgment",
                "claim notice date",
                claim_notice_at,
                ACKNOWLEDGMENT_WINDOW_DAYS,
                current_time,
            )
        )

    if proof_of_claim_at := _normalize_dt(proof_of_claim_at):
        windows.append(
            _build_window(
                "decision",
                "proof-of-claim date",
                proof_of_claim_at,
                DECISION_WINDOW_DAYS,
                current_time,
            )
        )

    return windows


def _should_alert(window: DeadlineWindow) -> bool:
    return window.is_overdue or window.days_remaining <= ai_config.deadline_alert_threshold_days


def _cooldown_elapsed(last_alert_at: datetime | None, now: datetime) -> bool:
    if last_alert_at is None:
        return True
    normalized_last_alert = _normalize_dt(last_alert_at)
    if normalized_last_alert is None:
        return True
    return now - normalized_last_alert >= timedelta(hours=ai_config.deadline_alert_cooldown_hours)


def _format_deadline_message(window: DeadlineWindow, *, stage: ChatStage) -> str:
    opener = "For reference: " if stage == ChatStage.STAGE_3 else ""
    status_text = "is overdue" if window.is_overdue else f"is due in {window.days_remaining} day(s)"
    body = (
        f"{opener}Deadline reminder: based on the {window.source_date_label} saved in this case, "
        f"the California {window.label} timeline is due on {window.due_at.date().isoformat()} and {status_text}. "
        "If the saved dates are incomplete or outdated, update them before relying on this reminder."
    )
    return f"{body}\n\n{DISCLAIMER_FOOTER}"


async def on_claim_dates_updated(
    case_id: str,
    claim_notice_at: datetime | None,
    proof_of_claim_at: datetime | None,
) -> None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        await session.execute(
            text(
                """
                UPDATE cases
                SET claim_notice_at = :claim_notice_at,
                    proof_of_claim_at = :proof_of_claim_at,
                    last_deadline_alert_at = NULL
                WHERE id = :case_id
                """
            ),
            {
                "case_id": case_id,
                "claim_notice_at": claim_notice_at,
                "proof_of_claim_at": proof_of_claim_at,
            },
        )
        await session.commit()


async def maybe_get_deadline_alert(case_id: str, *, stage: ChatStage) -> AIResponse | None:
    sessionmaker = get_sessionmaker()
    async with sessionmaker() as session:
        result = await session.execute(
            text(
                """
                SELECT claim_notice_at, proof_of_claim_at, last_deadline_alert_at
                FROM cases
                WHERE id = :case_id
                """
            ),
            {"case_id": case_id},
        )
        row = result.mappings().first()
        if row is None:
            return None

        now = datetime.now(UTC)
        windows = calculate_deadline_windows(
            claim_notice_at=row.get("claim_notice_at"),
            proof_of_claim_at=row.get("proof_of_claim_at"),
            now=now,
        )
        candidates = [window for window in windows if _should_alert(window)]
        if not candidates or not _cooldown_elapsed(row.get("last_deadline_alert_at"), now):
            return None

        target = sorted(candidates, key=lambda item: (item.is_overdue is False, item.days_remaining))[0]
        await session.execute(
            text(
                """
                UPDATE cases
                SET last_deadline_alert_at = :last_deadline_alert_at
                WHERE id = :case_id
                """
            ),
            {"case_id": case_id, "last_deadline_alert_at": now},
        )
        await session.commit()

    return AIResponse(
        text=_format_deadline_message(target, stage=stage),
        citations=[],
        trigger=AITrigger.DEADLINE,
        metadata={
            "deadline_type": target.label,
            "due_at": target.due_at.isoformat(),
            "days_remaining": target.days_remaining,
            "is_overdue": target.is_overdue,
        },
    )

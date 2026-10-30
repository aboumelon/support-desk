"""One lock order: conversation -> provider period -> workspace period -> run/job."""

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from supportdesk.modules.assistant.models import (
    AiAttempt,
    AiRun,
    ProviderUsagePeriod,
    UsagePeriod,
    UsageReservation,
)


def lock_provider(db: Session, run: AiRun) -> ProviderUsagePeriod:
    db.execute(text("SELECT pg_advisory_xact_lock(76124912, 1)"))
    db.execute(
        insert(ProviderUsagePeriod)
        .values(period=run.period, charged_tokens=0)
        .on_conflict_do_nothing()
    )
    period = db.scalar(
        select(ProviderUsagePeriod)
        .where(ProviderUsagePeriod.period == run.period)
        .with_for_update()
    )
    assert period is not None
    return period


def settle(db: Session, run: AiRun) -> None:
    provider = lock_provider(db, run)
    period = db.scalar(
        select(UsagePeriod)
        .where(
            UsagePeriod.workspace_id == run.workspace_id,
            UsagePeriod.period == run.period,
        )
        .with_for_update()
    )
    reservation = db.scalar(
        select(UsageReservation)
        .where(UsageReservation.ai_run_id == run.id)
        .with_for_update()
    )
    if period is None or reservation is None:
        return
    attempts = db.scalars(select(AiAttempt).where(AiAttempt.run_id == run.id)).all()
    charged = sum(
        (attempt.input_tokens or 0) + (attempt.output_tokens or 0)
        if attempt.usage_state == "known"
        else run.per_attempt_tokens
        for attempt in attempts
    )
    difference = charged - reservation.charged_tokens
    provider.charged_tokens += difference
    period.charged_tokens += difference
    reservation.charged_tokens, reservation.state = charged, "settled"

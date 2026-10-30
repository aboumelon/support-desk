from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import now
from supportdesk.modules.assistant.budgets import settle
from supportdesk.modules.assistant.models import (
    AiRun,
    ProviderUsagePeriod,
    UsagePeriod,
    UsageReservation,
)
from supportdesk.modules.conversations.models import Conversation
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.jobs.service import enqueue
from supportdesk.modules.knowledge.models import Document


async def ready(db: AsyncSession, workspace_id: object) -> bool:
    return bool(
        await db.scalar(
            select(Document.id)
            .where(
                Document.workspace_id == workspace_id,
                Document.active_version_id.is_not(None),
                Document.withdrawn_at.is_(None),
            )
            .limit(1)
        )
    )


async def supersede(db: AsyncSession, conversation: Conversation) -> None:
    runs = (
        await db.scalars(
            select(AiRun).where(
                AiRun.workspace_id == conversation.workspace_id,
                AiRun.conversation_id == conversation.id,
                AiRun.status.in_(["queued", "running"]),
            )
        )
    ).all()
    for run in runs:
        await db.run_sync(settle, run)
        run.status = "superseded"
        run.finished_at = now()
        job = await db.get(Job, run.job_id)
        if job:
            job.status = "cancelled"
            job.leased_until = None
        # The worker or reconciliation settles the reservation.


async def admit(db: AsyncSession, conversation: Conversation, message_seq: int) -> bool:
    settings = get_settings()
    if not settings.ai_enabled_for_public() or not await ready(
        db, conversation.workspace_id
    ):
        return False
    period = now().date()
    # Installation-wide admission is serialized even across different workspaces.
    from sqlalchemy import text

    await db.execute(text("SELECT pg_advisory_xact_lock(76124912, 1)"))
    await db.execute(
        insert(ProviderUsagePeriod)
        .values(period=period, charged_tokens=0)
        .on_conflict_do_nothing()
    )
    provider_usage = await db.scalar(
        select(ProviderUsagePeriod)
        .where(ProviderUsagePeriod.period == period)
        .with_for_update()
    )
    assert provider_usage is not None
    await db.execute(
        insert(UsagePeriod)
        .values(workspace_id=conversation.workspace_id, period=period, charged_tokens=0)
        .on_conflict_do_nothing()
    )
    usage = await db.scalar(
        select(UsagePeriod)
        .where(
            UsagePeriod.workspace_id == conversation.workspace_id,
            UsagePeriod.period == period,
        )
        .with_for_update()
    )
    assert usage is not None
    allowance = settings.input_allowance() + settings.ai_max_output_tokens
    reserved = allowance * 3
    queued = (
        await db.scalar(
            select(func.count())
            .select_from(AiRun)
            .where(
                AiRun.status.in_(["queued", "running"]),
            )
        )
        or 0
    )
    if (
        usage.charged_tokens + reserved > settings.ai_daily_token_limit
        or provider_usage.charged_tokens + reserved
        > settings.ai_provider_daily_token_limit
        or queued >= settings.ai_max_queued
    ):
        return False
    usage.charged_tokens += reserved
    provider_usage.charged_tokens += reserved
    run_id = uuid4()
    job = enqueue(db.sync_session, conversation.workspace_id, "ai", run_id)
    await db.flush()
    run = AiRun(
        id=run_id,
        workspace_id=conversation.workspace_id,
        conversation_id=conversation.id,
        trigger_message_seq=message_seq,
        expected_control_epoch=conversation.control_epoch,
        status="queued",
        provider_model="fixture-v1"
        if settings.llm_provider == "fake"
        else settings.llm_model,
        job_id=job.id,
        period=period,
        per_attempt_tokens=allowance,
    )
    db.add(run)
    await db.flush()
    db.add(
        UsageReservation(
            workspace_id=conversation.workspace_id,
            ai_run_id=run.id,
            reserved_tokens=reserved,
            charged_tokens=reserved,
        )
    )
    return True

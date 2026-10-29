from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import now
from supportdesk.modules.assistant.models import (
    AiAttempt,
    AiRun,
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
        usage = await db.scalar(
            select(UsagePeriod)
            .where(
                UsagePeriod.workspace_id == run.workspace_id,
                UsagePeriod.period == run.period,
            )
            .with_for_update()
        )
        reservation = await db.scalar(
            select(UsageReservation)
            .where(UsageReservation.ai_run_id == run.id)
            .with_for_update()
        )
        if usage is not None and reservation is not None:
            attempts = (
                await db.scalars(select(AiAttempt).where(AiAttempt.run_id == run.id))
            ).all()
            charged = sum(
                (a.input_tokens or 0) + (a.output_tokens or 0)
                if a.usage_state == "known"
                else run.per_attempt_tokens
                for a in attempts
            )
            usage.charged_tokens -= reservation.charged_tokens - charged
            reservation.charged_tokens, reservation.state = charged, "settled"
        run.status = "superseded"
        run.finished_at = now()
        job = await db.get(Job, run.job_id)
        if job:
            job.status = "cancelled"
            job.leased_until = None
        # The worker or reconciliation settles the reservation.


async def admit(db: AsyncSession, conversation: Conversation, message_seq: int) -> bool:
    settings = get_settings()
    if not await ready(db, conversation.workspace_id):
        return False
    period = now().date()
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
    allowance = settings.llm_context_limit or 8192
    reserved = allowance * 3
    queued = (
        await db.scalar(
            select(func.count())
            .select_from(AiRun)
            .where(
                AiRun.workspace_id == conversation.workspace_id,
                AiRun.status.in_(["queued", "running"]),
            )
        )
        or 0
    )
    if usage.charged_tokens + reserved > settings.ai_daily_token_limit or queued >= 10:
        return False
    usage.charged_tokens += reserved
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

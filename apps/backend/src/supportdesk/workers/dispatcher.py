"""Lease outbox rows, publish outside transactions, then acknowledge by token."""

import asyncio
import logging
from datetime import timedelta
from uuid import uuid4

from redis.asyncio import Redis
from sqlalchemy import or_, select, update

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session, now

# Register FK targets before ORM flush.
from supportdesk.modules.identity import models as identity
from supportdesk.modules.jobs.models import Job, Outbox
from supportdesk.modules.workspaces import models as workspaces

assert identity and workspaces
logger = logging.getLogger(__name__)


async def dispatch_once(redis: Redis) -> bool:
    token = uuid4()
    async with Session.begin() as db:
        row = await db.scalar(
            select(Outbox)
            .where(
                Outbox.status == "pending",
                Outbox.available_at <= now(),
                or_(Outbox.leased_until.is_(None), Outbox.leased_until < now()),
            )
            .order_by(Outbox.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if row is None:
            return False
        row.lease_token = token
        row.leased_until = now() + timedelta(seconds=30)
        row.attempts += 1
        row_id, workspace_id, reference_id = row.id, row.workspace_id, row.reference_id
        kind = row.kind
        job = await db.get(Job, reference_id) if kind == "job.dispatch" else None
        queue_name = "ai" if job and job.kind == "ai" else "ingestion"
    try:
        if kind == "job.dispatch":
            from supportdesk.workers.celery_app import app

            await asyncio.to_thread(
                app.send_task,
                "supportdesk.execute_job",
                args=[str(reference_id)],
                queue=queue_name,
                soft_time_limit=110 if queue_name == "ai" else 270,
                time_limit=120 if queue_name == "ai" else 300,
            )
        else:
            await redis.publish(f"sd:workspace:{workspace_id}", str(reference_id))
    except Exception:
        async with Session.begin() as db:
            await db.execute(
                update(Outbox)
                .where(Outbox.id == row_id, Outbox.lease_token == token)
                .values(leased_until=None, available_at=now() + timedelta(seconds=5))
            )
        logger.warning("outbox_transport_unavailable")
        return False
    async with Session.begin() as db:
        await db.execute(
            update(Outbox)
            .where(
                Outbox.id == row_id,
                Outbox.lease_token == token,
                Outbox.leased_until > now(),
            )
            .values(status="published", published_at=now(), leased_until=None)
        )
    return True


def recover_jobs() -> None:
    from sqlalchemy.orm import Session as SyncSession

    from supportdesk.infrastructure.worker_database import worker_engine
    from supportdesk.modules.assistant.finalization import recover_terminal_run
    from supportdesk.modules.assistant.models import AiRun
    from supportdesk.modules.jobs.service import reconcile

    with SyncSession(worker_engine()) as db, db.begin():
        reconcile(db)
        terminal = list(
            db.scalars(
                select(AiRun.id)
                .join(Job, AiRun.job_id == Job.id)
                .where(
                    AiRun.status.in_(["queued", "running"]),
                    Job.status.in_(["failed", "cancelled"]),
                )
                .limit(100)
            )
        )
    for run_id in terminal:
        with SyncSession(worker_engine()) as db, db.begin():
            recover_terminal_run(db, run_id)


async def main() -> None:
    redis = Redis.from_url(
        get_settings().redis_url, socket_connect_timeout=2, socket_timeout=2
    )
    last_recovery = 0.0
    try:
        while True:
            try:
                clock = asyncio.get_running_loop().time()
                if clock - last_recovery >= 15:
                    await asyncio.to_thread(recover_jobs)
                    last_recovery = clock
                for _ in range(100):
                    busy = await dispatch_once(redis)
                    if not busy:
                        break
            except Exception:
                logger.exception("dispatcher_iteration_failed")
                busy = False
            await asyncio.sleep(0.25)
    finally:
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(main())

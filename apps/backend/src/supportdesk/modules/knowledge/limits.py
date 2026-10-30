"""Installation-wide upload/storage admission shared by every demo workspace."""

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.api.errors import Problem
from supportdesk.config import get_settings
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.knowledge.models import Artifact


async def capacity(
    db: AsyncSession, incoming_bytes: int, ingestion: bool = False
) -> None:
    await db.execute(text("SELECT pg_advisory_xact_lock(76124912, 2)"))
    size = await db.scalar(
        select(func.coalesce(func.sum(Artifact.bytes), 0)).where(
            Artifact.state != "purged"
        )
    )
    if (size or 0) + incoming_bytes > get_settings().storage_max_bytes:
        raise Problem(429, "STORAGE_CAPACITY_REACHED")
    if ingestion:
        queued = await db.scalar(
            select(func.count())
            .select_from(Job)
            .where(
                Job.kind == "ingestion", Job.status.in_(["pending", "running", "retry"])
            )
        )
        if (queued or 0) >= get_settings().ingestion_max_queued:
            raise Problem(429, "INGESTION_CAPACITY_REACHED")

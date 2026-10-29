from datetime import timedelta
from uuid import UUID, uuid4

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from supportdesk.infrastructure.database import now
from supportdesk.modules.jobs.models import Job, Outbox
from supportdesk.modules.workspaces.models import Workspace


def enqueue(db: Session, workspace_id: UUID, kind: str, resource_id: UUID) -> Job:
    job = Job(
        id=uuid4(),
        workspace_id=workspace_id,
        kind=kind,
        resource_id=resource_id,
        logical_key=f"{kind}:{resource_id}",
        dispatch_generation=0,
        attempt=0,
        status="pending",
        available_at=now(),
    )
    db.add(job)
    db.add(
        Outbox(
            workspace_id=workspace_id,
            kind="job.dispatch",
            reference_id=job.id,
            dedupe_key=f"job:{job.id}:0",
        )
    )
    return job


def claim(db: Session, job_id: UUID) -> tuple[UUID, int] | None:
    job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None or job.status in {"succeeded", "failed", "cancelled"}:
        return None
    workspace = db.get(Workspace, job.workspace_id)
    if workspace is None or (workspace.expires_at and workspace.expires_at <= now()):
        job.status = "cancelled"
        return None
    if job.available_at > now() or (job.leased_until and job.leased_until > now()):
        return None
    if job.attempt >= 3:
        job.status = "failed"
        job.error_code = "ATTEMPTS_EXHAUSTED"
        return None
    token = uuid4()
    job.attempt += 1
    job.status = "running"
    job.lease_token = token
    job.leased_until = now() + timedelta(seconds=60)
    return token, job.attempt


def owns(job: Job, token: UUID) -> bool:
    return (
        job.status == "running"
        and job.lease_token == token
        and job.leased_until is not None
        and job.leased_until > now()
    )


def reconcile(db: Session) -> int:
    stamp = now()
    jobs = db.scalars(
        select(Job)
        .where(
            Job.status.in_(["pending", "running", "retry"]),
            Job.available_at <= stamp,
            or_(Job.leased_until.is_(None), Job.leased_until <= stamp),
            or_(
                Job.status == "running",
                Job.last_dispatched_at.is_(None),
                Job.last_dispatched_at < stamp - timedelta(seconds=120),
            ),
        )
        .with_for_update(skip_locked=True)
        .limit(100)
    ).all()
    count = 0
    for job in jobs:
        workspace = db.get(Workspace, job.workspace_id)
        if workspace is None or (
            workspace.expires_at and workspace.expires_at <= stamp
        ):
            job.status = "cancelled"
            continue
        if job.attempt >= 3:
            job.status = "failed"
            job.error_code = "ATTEMPTS_EXHAUSTED"
            continue
        job.status = "pending"
        job.leased_until = None
        job.dispatch_generation += 1
        job.last_dispatched_at = stamp
        db.add(
            Outbox(
                workspace_id=job.workspace_id,
                kind="job.dispatch",
                reference_id=job.id,
                dedupe_key=f"job:{job.id}:{job.dispatch_generation}",
            )
        )
        count += 1
    return count

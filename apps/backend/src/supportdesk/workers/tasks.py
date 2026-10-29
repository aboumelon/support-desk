import threading
from datetime import timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from supportdesk.infrastructure.database import now
from supportdesk.infrastructure.logging import job_event
from supportdesk.infrastructure.worker_database import worker_engine
from supportdesk.modules.identity import models as identity
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.jobs.service import claim, owns
from supportdesk.modules.knowledge.ingestion import ingest
from supportdesk.modules.knowledge.models import Document, DocumentVersion
from supportdesk.modules.knowledge.parsers import InvalidDocument
from supportdesk.workers.celery_app import app

assert identity


def heartbeat(job_id: UUID, token: UUID, stop: threading.Event) -> None:
    while not stop.wait(15):
        try:
            with Session(worker_engine()) as db, db.begin():
                result = db.execute(
                    update(Job)
                    .where(
                        Job.id == job_id,
                        Job.lease_token == token,
                        Job.status == "running",
                        Job.leased_until > now(),
                    )
                    .values(leased_until=now() + timedelta(seconds=60))
                    .returning(Job.id)
                )
                if result.scalar_one_or_none() is None:
                    return
        except Exception:
            return


def fail(job_id: UUID, token: UUID, code: str, terminal: bool) -> None:
    with Session(worker_engine()) as db, db.begin():
        info = db.get(Job, job_id)
        if info is None:
            return
        version = db.get(DocumentVersion, info.resource_id)
        if version:
            db.execute(
                select(Document)
                .where(Document.id == version.document_id)
                .with_for_update()
            )
            version = db.scalar(
                select(DocumentVersion)
                .where(DocumentVersion.id == version.id)
                .with_for_update()
            )
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        if job is None or not owns(job, token):
            return
        if version and version.status == "withdrawn":
            job.status = "cancelled"
            return
        job.error_code = code
        job.leased_until = None
        terminal = terminal or job.attempt >= 3
        job.status = "failed" if terminal else "retry"
        job.available_at = now() + timedelta(seconds=5 if job.attempt == 1 else 20)
        # A retry is eligible for reconciliation immediately after its backoff.
        job.last_dispatched_at = None
        if version:
            version.status = "failed" if terminal else "pending"
            version.error_code = code


@app.task(name="supportdesk.execute_job")  # type: ignore[untyped-decorator]
def execute_job(raw_job_id: str) -> None:
    job_id = UUID(raw_job_id)
    with Session(worker_engine()) as db, db.begin():
        claimed = claim(db, job_id)
        if claimed is None:
            return
        token, _ = claimed
        job = db.get(Job, job_id)
        assert job is not None
        kind = job.kind
    job_event("job.started", job_id=raw_job_id, kind=kind, attempt=claimed[1])
    stop = threading.Event()
    thread = threading.Thread(target=heartbeat, args=(job_id, token, stop), daemon=True)
    thread.start()
    try:
        if kind == "ai":
            from supportdesk.modules.assistant.generation import generate

            generate(job_id, token)
        elif kind == "ingestion":
            ingest(job_id, token)
        else:
            raise InvalidDocument("UNSUPPORTED_JOB_KIND")
    except InvalidDocument as exc:
        fail(job_id, token, str(exc), terminal=True)
    except (OSError, TimeoutError):
        fail(job_id, token, "TRANSIENT_IO_FAILURE", terminal=False)
    except Exception:
        if kind == "ai":
            from supportdesk.modules.assistant.finalization import finish

            with Session(worker_engine()) as db, db.begin():
                finish(db, job_id, token, None, "ASSISTANT_FAILED")
        else:
            fail(job_id, token, "INGESTION_FAILED", terminal=True)
    finally:
        stop.set()
        thread.join(timeout=1)
        job_event(
            "job.attempt_finished", job_id=raw_job_id, kind=kind, attempt=claimed[1]
        )

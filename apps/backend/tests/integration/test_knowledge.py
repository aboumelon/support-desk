import asyncio
from datetime import timedelta
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy.orm import Session as SyncSession

from supportdesk.infrastructure.database import Session, now
from supportdesk.infrastructure.worker_database import worker_engine
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.jobs.service import claim, owns, reconcile
from supportdesk.modules.knowledge.models import DocumentVersion
from supportdesk.workers.tasks import execute_job


async def upload(
    client: AsyncClient, text="Fictional support policy: contact the team."
):
    visitor = (await client.post("/api/v1/public/demo")).json()
    staff = (await client.get("/api/v1/auth/staff/me")).json()
    client.headers["X-CSRF-Token"] = staff["csrf_token"]
    url = f"/api/v1/staff/workspaces/{visitor['workspace_id']}/knowledge/documents"
    headers = {"Idempotency-Key": str(uuid4())}
    result = await client.post(
        url,
        headers=headers,
        data={"title": "Fictional policy"},
        files={"file": ("policy.md", text, "text/markdown")},
    )
    assert result.status_code == 202, result.text
    return url, headers, result.json()


async def test_upload_replay_withdrawal_and_tenant_access(client: AsyncClient):
    url, headers, original = await upload(client)
    result = await client.post(
        url,
        headers=headers,
        data={"title": "Fictional policy"},
        files={
            "file": (
                "policy.md",
                "Fictional support policy: contact the team.",
                "text/markdown",
            )
        },
    )
    assert result.status_code == 202
    assert result.json() == original
    assert (
        await client.post(
            url,
            headers=headers,
            data={"title": "Changed"},
            files={"file": ("policy.md", "different", "text/markdown")},
        )
    ).status_code == 409
    assert (await client.delete(f"{url}/{original['document_id']}")).status_code == 204
    await asyncio.to_thread(execute_job, original["job_id"])
    async with Session() as db:
        job = await db.get(Job, UUID(original["job_id"]))
        assert job.status == "cancelled"
        version = await db.get(DocumentVersion, UUID(original["version_id"]))
        assert version.status == "withdrawn"
    await client.post("/api/v1/public/demo")
    assert (await client.get(url)).status_code == 404


async def test_invalid_document_is_terminal_and_duplicate_task_is_noop(
    client: AsyncClient,
):
    _, _, original = await upload(client, text="\x00bad")
    await asyncio.to_thread(execute_job, original["job_id"])
    await asyncio.to_thread(execute_job, original["job_id"])
    async with Session() as db:
        job = await db.get(Job, UUID(original["job_id"]))
        assert job.status == "failed"
        assert job.error_code == "INVALID_TEXT"
        assert job.attempt == 1


async def test_expired_lease_recovery_and_fencing(client: AsyncClient):
    _, _, original = await upload(client)
    jid = UUID(original["job_id"])

    def check():
        with SyncSession(worker_engine()) as db, db.begin():
            token, attempt = claim(db, jid)
            assert attempt == 1
        with SyncSession(worker_engine()) as db, db.begin():
            assert claim(db, jid) is None
            job = db.get(Job, jid)
            job.leased_until = now() - timedelta(seconds=1)
            job.last_dispatched_at = now() - timedelta(seconds=121)
        with SyncSession(worker_engine()) as db, db.begin():
            assert reconcile(db) == 1
        with SyncSession(worker_engine()) as db, db.begin():
            second, attempt = claim(db, jid)
            assert attempt == 2 and second != token
            job = db.get(Job, jid)
            assert owns(job, second) and not owns(job, token)
            job.leased_until = now() - timedelta(seconds=1)
        with SyncSession(worker_engine()) as db, db.begin():
            _, attempt = claim(db, jid)
            assert attempt == 3
            job = db.get(Job, jid)
            job.leased_until = now() - timedelta(seconds=1)
        with SyncSession(worker_engine()) as db, db.begin():
            assert claim(db, jid) is None
            assert db.get(Job, jid).status == "failed"

    await asyncio.to_thread(check)

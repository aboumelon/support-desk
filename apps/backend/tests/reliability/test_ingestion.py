import asyncio
import os
import sys
from uuid import UUID

from httpx import AsyncClient
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session as SyncSession

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session
from supportdesk.infrastructure.worker_database import worker_engine
from supportdesk.modules.assistant.embeddings.e5 import encode
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.knowledge.models import KnowledgeChunk
from supportdesk.modules.knowledge.retrieval import retrieve
from supportdesk.workers.celery_app import app
from supportdesk.workers.dispatcher import dispatch_once

from ..integration.test_knowledge import upload


async def test_actual_celery_embedding_and_ready_only_retrieval(client: AsyncClient):
    url, _, original = await upload(
        client,
        text="# Fictional trial policy\n"
        "The fictional Tarvio trial lasts fourteen days. "
        "No payment card is needed.\n"
        "دوره آزمایشی تارویو چهارده روز است و نیازی به کارت پرداخت ندارد.",
    )
    async with Session() as db:
        job = await db.get(Job, UUID(original["job_id"]))
        workspace = job.workspace_id
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "celery",
        "-A",
        "supportdesk.workers.celery_app:app",
        "worker",
        "-Q",
        "ingestion",
        "--pool=solo",
        "--concurrency=1",
        "--loglevel=WARNING",
        env={**os.environ, "OMP_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false"},
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    redis = Redis.from_url(get_settings().redis_url)
    try:
        while await dispatch_once(redis):
            pass
        # A second actual broker delivery must not create duplicate chunks.
        await asyncio.to_thread(
            app.send_task,
            "supportdesk.execute_job",
            args=[original["job_id"]],
            queue="ingestion",
        )
        async with asyncio.timeout(90):
            while True:
                async with Session() as db:
                    job = await db.get(Job, UUID(original["job_id"]))
                    if job.status in {"succeeded", "failed"}:
                        assert job.status == "succeeded", job.error_code
                        assert job.attempt == 1
                        break
                await asyncio.sleep(0.25)
        vector = (
            await asyncio.to_thread(encode, ["How long is the Tarvio trial?"], "query")
        )[0]

        def check():
            with SyncSession(worker_engine()) as db:
                found = retrieve(db, workspace, vector)
                assert len(found) == 1
                assert "fourteen days" in found[0].chunk.text
                assert db.scalar(select(func.count()).select_from(KnowledgeChunk)) == 1

        await asyncio.to_thread(check)
        # A replacement pending version leaves the prior version retrievable.
        result = await client.post(
            f"{url}/{original['document_id']}/versions",
            headers={"Idempotency-Key": "replacement"},
            data={"title": "Trial v2"},
            files={
                "file": ("trial.md", "Trial now lasts seven days.", "text/markdown")
            },
        )
        assert result.status_code == 202
        await asyncio.to_thread(check)
        assert (
            await client.delete(f"{url}/{original['document_id']}")
        ).status_code == 204

        def withdrawn():
            with SyncSession(worker_engine()) as db:
                assert retrieve(db, workspace, vector) == []

        await asyncio.to_thread(withdrawn)
    finally:
        await redis.aclose()
        process.terminate()
        await asyncio.wait_for(process.wait(), 15)

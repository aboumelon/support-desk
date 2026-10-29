import asyncio
import os
import signal
import sys
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import select

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session, now
from supportdesk.modules.assistant.models import AiRun
from supportdesk.modules.jobs.models import Job
from supportdesk.workers.celery_app import app
from supportdesk.workers.dispatcher import dispatch_once, recover_jobs

from ..integration.test_assistant import prepare


async def worker(scenario):
    return await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "celery",
        "-A",
        "supportdesk.workers.celery_app:app",
        "worker",
        "-Q",
        "ai",
        "--pool=solo",
        "--concurrency=1",
        "--loglevel=WARNING",
        env={**os.environ, "FAKE_SCENARIO": scenario, "OMP_NUM_THREADS": "1"},
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )


async def test_actual_worker_kill_lease_expiry_and_queue_reconstruction(client):
    _, _, _, jid = await prepare(client)
    redis = Redis.from_url(get_settings().redis_url)
    await redis.delete("sd:broker:ai")
    first = await worker("slow")
    second = None
    try:
        await asyncio.to_thread(
            app.send_task, "supportdesk.execute_job", args=[jid], queue="ai"
        )
        async with asyncio.timeout(30):
            while True:
                async with Session() as db:
                    run = await db.scalar(select(AiRun))
                    if run.status == "running":
                        break
                await asyncio.sleep(0.025)
        first.send_signal(signal.SIGKILL)
        await first.wait()
        # Wait for the actual durable lease clock to expire.
        async with asyncio.timeout(75):
            while True:
                async with Session() as db:
                    job = await db.get(Job, UUID(jid))
                    if job.leased_until <= now():
                        break
                await asyncio.sleep(0.25)
        await redis.delete("sd:broker:ai")
        await asyncio.to_thread(recover_jobs)
        while await dispatch_once(redis):
            pass
        second = await worker("normal")
        async with asyncio.timeout(40):
            while True:
                async with Session() as db:
                    job = await db.get(Job, UUID(jid))
                    if job.status in {"succeeded", "failed"}:
                        assert job.status == "succeeded", job.error_code
                        assert job.attempt == 2
                        break
                await asyncio.sleep(0.1)
    finally:
        if first.returncode is None:
            first.kill()
            await first.wait()
        if second and second.returncode is None:
            second.terminate()
            await asyncio.wait_for(second.wait(), 15)
        await redis.aclose()

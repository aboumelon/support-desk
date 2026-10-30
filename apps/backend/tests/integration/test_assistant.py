import asyncio
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session
from supportdesk.modules.assistant.models import AiAttempt, AiRun, UsageReservation
from supportdesk.modules.assistant.providers.base import Delta
from supportdesk.modules.assistant.providers.fake import FakeProvider
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.messaging.models import Message
from supportdesk.modules.workspaces.models import Workspace
from supportdesk.workers.tasks import execute_job

from .test_knowledge import upload


async def prepare(client: AsyncClient):
    url, _, original = await upload(
        client,
        text="# Tarvio trial\nThe fictional Tarvio trial lasts fourteen days. "
        "No credit card is needed.",
    )
    await asyncio.to_thread(execute_job, original["job_id"])
    workspace = url.split("/")[5]
    async with Session.begin() as db:
        item = await db.get(Workspace, UUID(workspace))
        item.ai_enabled = True
    visitor = (await client.get("/api/v1/customer/session")).json()
    client.headers["X-CSRF-Token"] = visitor["csrf_token"]
    conversation = (
        await client.post(
            "/api/v1/customer/conversations", headers={"Idempotency-Key": str(uuid4())}
        )
    ).json()
    assert conversation["controller"] == "bot"
    prefix = f"/api/v1/customer/conversations/{conversation['id']}"
    response = await client.post(
        prefix + "/messages",
        json={
            "client_message_id": str(uuid4()),
            "body": "How long is the Tarvio trial?",
        },
    )
    assert response.status_code == 201, response.text
    async with Session() as db:
        run = await db.scalar(select(AiRun))
        jid = str(run.job_id)
    return prefix, url, original, jid


async def test_fake_answer_citation_and_accounting(client: AsyncClient):
    prefix, _, _, jid = await prepare(client)
    await asyncio.to_thread(execute_job, jid)
    await asyncio.to_thread(execute_job, jid)
    snapshot = (await client.get(prefix + "/snapshot")).json()
    assert len(snapshot["messages"]) == 2
    message = snapshot["messages"][-1]
    assert message["sender_kind"] == "assistant"
    assert "[S1]" in message["body"]
    source = await client.get(f"{prefix}/citations/{message['id']}/S1")
    assert source.status_code == 200 and "fourteen" in source.json()["excerpt"]
    async with Session() as db:
        assert (
            await db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.sender_kind == "assistant")
            )
            == 1
        )
        reservation = await db.scalar(select(UsageReservation))
        assert reservation.state == "settled"
        assert reservation.charged_tokens < reservation.reserved_tokens


async def test_stale_prompt_version_hands_off_without_inference(client: AsyncClient):
    prefix, _, _, jid = await prepare(client)
    async with Session.begin() as db:
        run = await db.scalar(select(AiRun))
        run.prompt_version = "answer-v2"
    await asyncio.to_thread(execute_job, jid)
    snapshot = (await client.get(prefix + "/snapshot")).json()
    assert snapshot["conversation"]["controller"] == "queue"
    assert len(snapshot["messages"]) == 1
    assert snapshot["active_run"]["error_code"] == "ASSISTANT_FAILED"
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(AiAttempt)) == 0


async def test_citation_only_answer_is_not_published(client: AsyncClient, monkeypatch):
    def citation_only(*args):
        yield Delta(text="[S1]", input_tokens=10, output_tokens=2)

    monkeypatch.setattr(FakeProvider, "stream", citation_only)
    prefix, _, _, jid = await prepare(client)
    await asyncio.to_thread(execute_job, jid)
    snapshot = (await client.get(prefix + "/snapshot")).json()
    assert snapshot["conversation"]["controller"] == "queue"
    assert len(snapshot["messages"]) == 1
    assert snapshot["active_run"]["error_code"] == "INVALID_CITATION"


@pytest.mark.parametrize("race", ["handoff", "new_turn", "withdraw"])
async def test_slow_generation_fences(client: AsyncClient, monkeypatch, race):
    monkeypatch.setattr(get_settings(), "fake_scenario", "slow")
    prefix, url, original, jid = await prepare(client)
    work = asyncio.create_task(asyncio.to_thread(execute_job, jid))
    async with asyncio.timeout(15):
        while True:
            async with Session() as db:
                run = await db.scalar(select(AiRun))
                if run.status == "running":
                    break
            await asyncio.sleep(0.025)
    if race == "handoff":
        response = await client.post(
            prefix + "/handoff",
            headers={"Idempotency-Key": str(uuid4())},
            json={"expected_state_version": 1},
        )
        assert response.status_code == 200
    elif race == "new_turn":
        response = await client.post(
            prefix + "/messages",
            json={
                "client_message_id": str(uuid4()),
                "body": "Please also clarify payment cards",
            },
        )
        assert response.status_code == 201
    else:
        staff = (await client.get("/api/v1/auth/staff/me")).json()
        response = await client.delete(
            f"{url}/{original['document_id']}",
            headers={"X-CSRF-Token": staff["csrf_token"]},
        )
        assert response.status_code == 204
    await work
    async with Session() as db:
        assert (
            await db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.sender_kind == "assistant")
            )
            == 0
        )
        old = await db.get(Job, UUID(jid))
        assert old.status in {"cancelled", "failed"}


async def test_invalid_citation_hands_off_without_final_message(
    client: AsyncClient, monkeypatch
):
    monkeypatch.setattr(get_settings(), "fake_scenario", "invalid_citation")
    prefix, _, _, jid = await prepare(client)
    await asyncio.to_thread(execute_job, jid)
    snapshot = (await client.get(prefix + "/snapshot")).json()
    assert snapshot["conversation"]["controller"] == "queue"
    assert len(snapshot["messages"]) == 1
    assert snapshot["active_run"]["error_code"] == "INVALID_CITATION"


async def test_budget_rejection_keeps_customer_message(
    client: AsyncClient, monkeypatch
):
    prefix, _, _, jid = await prepare(client)
    monkeypatch.setattr(get_settings(), "ai_daily_token_limit", 1)
    response = await client.post(
        prefix + "/messages",
        json={"client_message_id": str(uuid4()), "body": "A new turn after the cap"},
    )
    assert response.status_code == 201
    assert response.json()["conversation"]["controller"] == "queue"
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(Message)) == 2
        reservation = await db.scalar(select(UsageReservation))
        assert reservation.state == "settled" and reservation.charged_tokens == 0


@pytest.mark.parametrize("scenario", ["timeout", "429", "drop"])
async def test_bounded_provider_failures_keep_unknown_usage(
    client: AsyncClient, monkeypatch, scenario
):
    monkeypatch.setattr(get_settings(), "fake_scenario", scenario)
    prefix, _, _, jid = await prepare(client)
    from supportdesk.infrastructure.database import now

    for _ in range(3):
        await asyncio.to_thread(execute_job, jid)
        async with Session.begin() as db:
            job = await db.get(Job, UUID(jid))
            job.available_at = now()
    snapshot = (await client.get(prefix + "/snapshot")).json()
    assert snapshot["conversation"]["controller"] == "queue"
    assert len(snapshot["messages"]) == 1
    async with Session() as db:
        job = await db.get(Job, UUID(jid))
        assert job.attempt == 3 and job.status == "failed"
        reservation = await db.scalar(select(UsageReservation))
        assert reservation.state == "settled"
        assert reservation.charged_tokens == reservation.reserved_tokens


@pytest.mark.parametrize("race", ["lease_replaced", "source_replaced"])
async def test_finalization_rejects_stale_lease_and_replaced_version(
    client: AsyncClient, monkeypatch, race
):
    from datetime import timedelta

    from supportdesk.infrastructure.database import now
    from supportdesk.modules.knowledge.models import Document, DocumentVersion

    monkeypatch.setattr(get_settings(), "fake_scenario", "slow")
    _, _, original, jid = await prepare(client)
    work = asyncio.create_task(asyncio.to_thread(execute_job, jid))
    async with asyncio.timeout(15):
        while True:
            async with Session() as db:
                run = await db.scalar(select(AiRun))
                if run.status == "running":
                    break
            await asyncio.sleep(0.025)
    async with Session.begin() as db:
        if race == "lease_replaced":
            job = await db.get(Job, UUID(jid))
            job.lease_token = uuid4()
            job.leased_until = now() + timedelta(seconds=60)
        else:
            original_version = await db.get(
                DocumentVersion, UUID(original["version_id"])
            )
            replacement = DocumentVersion(
                id=uuid4(),
                workspace_id=original_version.workspace_id,
                document_id=original_version.document_id,
                artifact_id=original_version.artifact_id,
                version_no=2,
                status="ready",
                embedding_model=original_version.embedding_model,
                embedding_revision=original_version.embedding_revision,
                content_hash=original_version.content_hash,
            )
            db.add(replacement)
            await db.flush()
            document = await db.get(Document, original_version.document_id)
            document.active_version_id = replacement.id
    await work
    async with Session() as db:
        assert (
            await db.scalar(
                select(func.count())
                .select_from(Message)
                .where(Message.sender_kind == "assistant")
            )
            == 0
        )
        if race == "source_replaced":
            run = await db.scalar(select(AiRun))
            assert run.error_code == "KNOWLEDGE_CHANGED"


async def test_exhausted_crashed_job_hands_off_and_releases_never_started_usage(
    client: AsyncClient,
):
    from datetime import timedelta

    from supportdesk.infrastructure.database import now
    from supportdesk.workers.dispatcher import recover_jobs

    prefix, _, _, jid = await prepare(client)
    async with Session.begin() as db:
        job = await db.get(Job, UUID(jid))
        job.status = "running"
        job.attempt = 3
        job.leased_until = now() - timedelta(seconds=1)
    await asyncio.to_thread(recover_jobs)
    snapshot = (await client.get(prefix + "/snapshot")).json()
    assert snapshot["conversation"]["controller"] == "queue"
    assert snapshot["active_run"]["status"] == "failed"
    async with Session() as db:
        reservation = await db.scalar(select(UsageReservation))
        assert reservation.charged_tokens == 0 and reservation.state == "settled"

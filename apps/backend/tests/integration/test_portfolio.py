import asyncio
import hashlib
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session as SyncSession
from starlette.requests import Request

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session, now
from supportdesk.infrastructure.worker_database import worker_engine
from supportdesk.main import create_app
from supportdesk.modules.assistant.budgets import settle
from supportdesk.modules.assistant.models import (
    AiAttempt,
    AiRun,
    ProviderUsagePeriod,
    UsagePeriod,
    UsageReservation,
)
from supportdesk.modules.conversations.models import Conversation
from supportdesk.modules.identity.service import remote_identity
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.jobs.service import claim
from supportdesk.modules.knowledge.limits import capacity
from supportdesk.modules.messaging.models import Message
from supportdesk.workers.tasks import execute_job

from .test_knowledge import upload


def new_client():
    return AsyncClient(
        transport=ASGITransport(app=create_app()),
        base_url="http://test",
        headers={"Origin": "http://localhost:5173"},
    )


async def ready_conversation(client):
    _, _, original = await upload(
        client, text="The fictional Tarvio trial lasts fourteen days."
    )
    await asyncio.to_thread(execute_job, original["job_id"])
    staff = (await client.get("/api/v1/auth/staff/me")).json()
    workspace = staff["memberships"][0]["workspace_id"]
    assert (
        await client.put(
            f"/api/v1/staff/workspaces/{workspace}/assistant",
            headers={"X-CSRF-Token": staff["csrf_token"]},
            json={"enabled": True},
        )
    ).status_code == 200
    visitor = (await client.get("/api/v1/customer/session")).json()
    client.headers["X-CSRF-Token"] = visitor["csrf_token"]
    conversation = (
        await client.post(
            "/api/v1/customer/conversations", headers={"Idempotency-Key": str(uuid4())}
        )
    ).json()
    return conversation["id"]


async def send(client, cid):
    return await client.post(
        f"/api/v1/customer/conversations/{cid}/messages",
        json={
            "client_message_id": str(uuid4()),
            "body": "How long is the Tarvio trial?",
        },
    )


async def test_global_budget_is_atomic_across_workspaces_and_large_context(
    client, monkeypatch
):
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_context_limit", 1048576)
    reserved = (settings.ai_max_input_tokens + settings.ai_max_output_tokens) * 3
    monkeypatch.setattr(settings, "ai_provider_daily_token_limit", reserved)
    async with new_client() as other:
        first, second = (
            await ready_conversation(client),
            await ready_conversation(other),
        )
        responses = await asyncio.gather(send(client, first), send(other, second))
    assert all(response.status_code == 201 for response in responses)
    assert sorted(
        response.json()["conversation"]["controller"] for response in responses
    ) == ["bot", "queue"]
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(Message)) == 2
        runs = (await db.scalars(select(AiRun))).all()
        assert len(runs) == 1 and runs[0].per_attempt_tokens == reserved // 3
        ledger = await db.scalar(select(ProviderUsagePeriod))
        assert ledger.charged_tokens == reserved


async def test_global_concurrency_and_reservation_reconciliation(client, monkeypatch):
    async with new_client() as other:
        first, second = (
            await ready_conversation(client),
            await ready_conversation(other),
        )
        await send(client, first)
        await send(other, second)
    async with Session() as db:
        jobs = (await db.scalars(select(Job.id).where(Job.kind == "ai"))).all()

    def compete(jid):
        with SyncSession(worker_engine()) as db, db.begin():
            return claim(db, jid)

    claims = await asyncio.gather(*(asyncio.to_thread(compete, jid) for jid in jobs))
    assert sum(value is not None for value in claims) == 1
    winner = next(i for i, value in enumerate(claims) if value)
    async with Session.begin() as db:
        job = await db.get(Job, jobs[winner])
        job.leased_until = now() - timedelta(seconds=1)
        waiting = await db.get(Job, jobs[1 - winner])
        waiting.available_at = now()
    assert await asyncio.to_thread(compete, jobs[1 - winner]) is not None
    async with Session.begin() as db:
        runs = (await db.scalars(select(AiRun).order_by(AiRun.id))).all()
        for index, run in enumerate(runs):
            db.add(
                AiAttempt(
                    workspace_id=run.workspace_id,
                    run_id=run.id,
                    attempt=1,
                    usage_state="known" if index == 0 else "unknown",
                    input_tokens=80 if index == 0 else None,
                    output_tokens=20 if index == 0 else None,
                )
            )
        await db.flush()
        for run in runs:
            await db.run_sync(settle, run)
        provider = await db.scalar(select(ProviderUsagePeriod))
        assert provider.charged_tokens == 100 + runs[1].per_attempt_tokens
        assert (
            sum((await db.scalars(select(UsagePeriod.charged_tokens))).all())
            == provider.charged_tokens
        )


async def test_search_all_pages_ties_previews_references_and_authorization(client):
    identity = (await client.post("/api/v1/public/demo")).json()
    wid, actor = UUID(identity["workspace_id"]), UUID(identity["actor_id"])
    stamp = now()
    ids = []
    async with Session.begin() as db:
        for index in range(67):
            cid = uuid4()
            ids.append(cid)
            body = f"پرسش **پیگیری** شماره {index}" + (
                " پرداخت ابری 100%_special" if index == 0 else ""
            )
            db.add(
                Conversation(
                    id=cid,
                    workspace_id=wid,
                    visitor_actor_id=actor,
                    controller="queue",
                    last_event_seq=1,
                    updated_at=stamp - timedelta(days=1) if index == 0 else stamp,
                )
            )
            await db.flush()
            db.add(
                Message(
                    workspace_id=wid,
                    conversation_id=cid,
                    sender_actor_id=actor,
                    sender_kind="visitor",
                    client_message_id=uuid4(),
                    body=body,
                    body_hash=hashlib.sha256(body.encode()).hexdigest(),
                    event_seq=1,
                )
            )
    url = f"/api/v1/staff/workspaces/{wid}/conversations"
    cursor = None
    found = []
    while True:
        response = await client.get(
            url,
            params={"q": "پرسش", "limit": 7, **({"cursor": cursor} if cursor else {})},
        )
        assert response.status_code == 200, response.text
        for item in response.json():
            assert "**" not in item["title"] and item["last_message_preview"]
            found.append(item["id"])
        cursor = response.headers.get("X-Next-Cursor")
        if not cursor:
            break
    assert len(found) == len(set(found)) == 67 and found[-1] == str(ids[0])
    for value in ["پرداخت ابری", "%_", "#" + str(ids[0]).replace("-", "")[:8]]:
        response = await client.get(url, params={"q": value})
        assert [item["id"] for item in response.json()] == [str(ids[0])]
    assert (await client.get(url, params={"cursor": "garbage"})).status_code == 422
    assert (await client.get(url, params={"q": "a"})).status_code == 422
    async with new_client() as other:
        await other.post(
            f"/api/v1/public/workspaces/{identity['public_key']}/visitor-sessions"
        )
        assert (
            await other.get("/api/v1/customer/conversations", params={"q": "پرسش"})
        ).json() == []
        await other.post("/api/v1/public/demo")
        assert (await other.get(url, params={"q": "پرسش"})).status_code == 404


async def test_customer_entry_capability_requires_local_seed(client, monkeypatch):
    from supportdesk.cli.seed_demo import seed

    assert (
        "customer_entry_key"
        not in (await client.get("/api/v1/public/capabilities")).json()
    )
    await seed()
    caps = (await client.get("/api/v1/public/capabilities")).json()
    assert caps["customer_entry_key"] == "tarvio-demo"
    monkeypatch.setattr(get_settings(), "app_env", "production")
    assert (
        "customer_entry_key"
        not in (await client.get("/api/v1/public/capabilities")).json()
    )
    assert (
        await client.post("/api/v1/public/workspaces/tarvio-demo/visitor-sessions")
    ).status_code == 404


async def test_public_capabilities_and_shared_creation_limit(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_mode", False)
    caps = (await client.get("/api/v1/public/capabilities")).json()
    assert caps == {"demo_available": False, "ai_mode": "simulated"}
    assert (await client.post("/api/v1/public/demo")).status_code == 404
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "demo_daily_limit", 1)
    assert (await client.post("/api/v1/public/demo")).status_code == 200
    async with new_client() as other:
        assert (await other.post("/api/v1/public/demo")).status_code == 429
    monkeypatch.setattr(settings, "llm_provider", "compatible_http")
    monkeypatch.setattr(settings, "app_env", "production")
    caps = (await client.get("/api/v1/public/capabilities")).json()
    assert caps["ai_mode"] == "disabled"
    assert not settings.ai_enabled_for_public()
    assert set(caps) == {"demo_available", "ai_mode"}


async def test_storage_and_ingestion_limit_is_shared(client, monkeypatch):
    from supportdesk.api.errors import Problem

    await upload(client, text="First persisted file")
    async with new_client() as other:
        await upload(other, text="Second persisted file")
    monkeypatch.setattr(get_settings(), "ingestion_max_queued", 2)
    async with Session.begin() as db:
        with pytest.raises(Problem, match="INGESTION_CAPACITY_REACHED"):
            await capacity(db, 0, ingestion=True)
    monkeypatch.setattr(get_settings(), "storage_max_bytes", 1)
    async with Session.begin() as db:
        with pytest.raises(Problem, match="STORAGE_CAPACITY_REACHED"):
            await capacity(db, 0)


@pytest.mark.parametrize(
    "peer,forwarded,expected",
    [
        ("203.0.113.20", "198.51.100.1", "203.0.113.20"),
        ("172.30.29.2", "198.51.100.1", "198.51.100.1"),
        ("172.30.29.2", "198.51.100.9, 198.51.100.1", "198.51.100.1"),
        ("172.30.29.2", "invalid", "172.30.29.2"),
    ],
)
def test_forwarded_identity_trusts_only_explicit_proxy(
    monkeypatch, peer, forwarded, expected
):
    monkeypatch.setattr(get_settings(), "trusted_proxies", ["172.30.29.2/32"])
    request = Request(
        {
            "type": "http",
            "client": (peer, 1234),
            "headers": [(b"x-forwarded-for", forwarded.encode())],
        }
    )
    assert remote_identity(request) == expected


async def test_expiry_cannot_refund_unknown_provider_usage(client, monkeypatch):
    from supportdesk.cli.purge_expired import main as purge
    from supportdesk.modules.workspaces.models import Workspace

    cid = await ready_conversation(client)
    await send(client, cid)
    async with Session.begin() as db:
        run = await db.scalar(select(AiRun))
        per_attempt = run.per_attempt_tokens
        reserved = per_attempt * 3
        workspace = await db.get(Workspace, run.workspace_id)
        workspace.expires_at = now() - timedelta(seconds=1)
        db.add(
            AiAttempt(
                workspace_id=run.workspace_id,
                run_id=run.id,
                attempt=1,
                usage_state="unknown",
            )
        )
    await asyncio.to_thread(purge)
    async with Session() as db:
        assert (
            await db.scalar(select(ProviderUsagePeriod.charged_tokens)) == per_attempt
        )
        assert await db.scalar(select(func.count()).select_from(UsageReservation)) == 0
    monkeypatch.setattr(get_settings(), "ai_provider_daily_token_limit", reserved)
    async with new_client() as other:
        second = await ready_conversation(other)
        response = await send(other, second)
        assert (
            response.status_code == 201
            and response.json()["conversation"]["controller"] == "queue"
        )

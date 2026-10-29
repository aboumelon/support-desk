import asyncio
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from supportdesk.infrastructure.database import Session
from supportdesk.modules.conversations.models import Conversation
from supportdesk.modules.conversations.schemas import MessageInput
from supportdesk.modules.conversations.service import send
from supportdesk.modules.jobs.models import Outbox
from supportdesk.modules.messaging.models import ConversationEvent, Message
from supportdesk.modules.workspaces.models import Actor


async def setup(client: AsyncClient):
    identity = (await client.post("/api/v1/public/demo")).json()
    client.headers["X-CSRF-Token"] = identity["csrf_token"]
    response = await client.post(
        "/api/v1/customer/conversations", headers={"Idempotency-Key": str(uuid4())}
    )
    assert response.status_code == 200, response.text
    return identity, response.json()


async def test_concurrent_retry_and_ordering(client: AsyncClient):
    identity, conversation = await setup(client)
    cid = conversation["id"]
    from uuid import UUID

    actor_id = UUID(identity["actor_id"])
    body = MessageInput(client_message_id=uuid4(), body="Concurrent fictional message")

    async def deliver(payload):
        async with Session.begin() as db:
            actor = await db.get(Actor, actor_id)
            assert actor is not None
            return await send(db, actor, UUID(cid), payload)

    results = await asyncio.gather(*(deliver(body) for _ in range(8)))
    assert sum(created for _, created in results) == 1
    assert len({result.message.id for result, _ in results}) == 1
    results = await asyncio.gather(
        *(
            deliver(MessageInput(client_message_id=uuid4(), body=f"Turn {i}"))
            for i in range(8)
        )
    )
    assert sorted(result.message.event_seq for result, _ in results) == list(
        range(3, 11)
    )
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(Message)) == 9
        assert (
            await db.scalar(select(func.count()).select_from(ConversationEvent)) == 10
        )
        assert await db.scalar(select(func.count()).select_from(Outbox)) == 10


async def test_replay_conflict_snapshot_and_receipts(client: AsyncClient):
    _, conversation = await setup(client)
    prefix = f"/api/v1/customer/conversations/{conversation['id']}"
    payload = {"client_message_id": str(uuid4()), "body": "سلام، این پیام آزمایشی است"}
    response = await client.post(prefix + "/messages", json=payload)
    assert response.status_code == 201
    message = response.json()["message"]
    assert (await client.post(prefix + "/messages", json=payload)).status_code == 200
    payload["body"] = "different"
    assert (await client.post(prefix + "/messages", json=payload)).status_code == 409
    read = {"last_read_seq": message["event_seq"]}
    assert (await client.put(prefix + "/read-cursor", json=read)).status_code == 200
    assert (await client.put(prefix + "/read-cursor", json=read)).status_code == 200
    snapshot = (await client.get(prefix + "/snapshot")).json()
    assert snapshot["event_cursor"] == 3
    assert len(snapshot["messages"]) == 1
    assert (
        await client.put(prefix + "/read-cursor", json={"last_read_seq": 3})
    ).status_code == 422
    await client.post("/api/v1/public/demo")
    assert (await client.get(prefix + "/snapshot")).status_code == 404


async def test_existing_retry_survives_resolution(client: AsyncClient):
    _, conversation = await setup(client)
    prefix = f"/api/v1/customer/conversations/{conversation['id']}"
    payload = {"client_message_id": str(uuid4()), "body": "Keep original identity"}
    original = (await client.post(prefix + "/messages", json=payload)).json()
    from uuid import UUID

    async with Session.begin() as db:
        item = await db.get(Conversation, UUID(conversation["id"]))
        item.status = "resolved"
    retry = await client.post(prefix + "/messages", json=payload)
    assert retry.status_code == 200
    assert retry.json()["message"]["id"] == original["message"]["id"]
    assert retry.json()["conversation"]["status"] == "resolved"
    payload["client_message_id"] = str(uuid4())
    assert (await client.post(prefix + "/messages", json=payload)).status_code == 409


async def test_cross_workspace_fk(client: AsyncClient):
    first, _ = await setup(client)
    second = (await client.post("/api/v1/public/demo")).json()
    from uuid import UUID

    with pytest.raises(IntegrityError):
        async with Session.begin() as db:
            db.add(
                Conversation(
                    workspace_id=UUID(second["workspace_id"]),
                    visitor_actor_id=UUID(first["actor_id"]),
                )
            )


async def test_create_command_replay(client: AsyncClient):
    await setup(client)
    key = str(uuid4())
    responses = await asyncio.gather(
        *(
            client.post(
                "/api/v1/customer/conversations", headers={"Idempotency-Key": key}
            )
            for _ in range(4)
        )
    )
    assert all(r.status_code == 200 for r in responses)
    assert len({r.json()["id"] for r in responses}) == 1

import asyncio
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import select

from supportdesk.api.errors import Problem
from supportdesk.infrastructure.database import Session
from supportdesk.modules.conversations.control import control
from supportdesk.modules.conversations.schemas import ControlInput
from supportdesk.modules.identity.models import StaffUser
from supportdesk.modules.identity.service import DUMMY_HASH
from supportdesk.modules.workspaces.models import Actor


async def test_competing_claims_and_receipt_recovery(client: AsyncClient):
    identity = (await client.post("/api/v1/public/demo")).json()
    client.headers["X-CSRF-Token"] = identity["csrf_token"]
    conversation = (
        await client.post(
            "/api/v1/customer/conversations", headers={"Idempotency-Key": str(uuid4())}
        )
    ).json()
    workspace_id, cid = UUID(identity["workspace_id"]), UUID(conversation["id"])
    async with Session.begin() as db:
        first = await db.scalar(
            select(Actor).where(
                Actor.workspace_id == workspace_id, Actor.kind == "staff"
            )
        )
        user = StaffUser(
            normalized_email="second@demo.invalid", password_hash=DUMMY_HASH
        )
        db.add(user)
        await db.flush()
        second = Actor(
            workspace_id=workspace_id,
            kind="staff",
            user_id=user.id,
            role="agent",
            display_name="Second fictional agent",
        )
        db.add(second)
        await db.flush()
        actor_ids = [first.id, second.id]
    keys = [str(uuid4()), str(uuid4())]

    async def claim(index):
        try:
            async with Session.begin() as db:
                actor = await db.get(Actor, actor_ids[index])
                return await control(
                    db,
                    actor,
                    cid,
                    "claim",
                    ControlInput(expected_state_version=1),
                    keys[index],
                )
        except Problem as exc:
            return exc.code

    results = await asyncio.gather(claim(0), claim(1))
    assert sum(isinstance(result, str) for result in results) == 1
    assert "CONVERSATION_VERSION_CONFLICT" in results
    winner = next(i for i, result in enumerate(results) if not isinstance(result, str))
    recovered = await claim(winner)
    assert recovered.state_version == 2
    assert recovered.assigned_actor_id == actor_ids[winner]
    async with Session.begin() as db:
        customer = await db.get(Actor, UUID(identity["actor_id"]))
        handoff = await control(
            db,
            customer,
            cid,
            "handoff",
            ControlInput(expected_state_version=1),
            str(uuid4()),
        )
        assert handoff.assigned_actor_id == actor_ids[winner]

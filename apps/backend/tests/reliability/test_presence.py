import asyncio
import json
import time
from uuid import UUID, uuid4

import pytest
from redis.asyncio import Redis
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session
from supportdesk.modules.conversations.service import create_conversation
from supportdesk.modules.realtime.presence import update_presence
from supportdesk.modules.workspaces.models import Actor
from tests.reliability.test_realtime import api_process


async def test_presence_keeps_other_tabs_online_and_removes_expired_members():
    redis = Redis.from_url(get_settings().redis_url)
    workspace, conversation, actor, other, first, second = [uuid4() for _ in range(6)]
    key = f"sd:presence:{workspace}:{conversation}"
    try:
        assert await update_presence(redis, workspace, conversation, actor, first) == {
            actor
        }
        assert await update_presence(redis, workspace, conversation, actor, second) == {
            actor
        }
        assert await update_presence(
            redis, workspace, conversation, actor, first, online=False
        ) == {actor}
        await redis.zadd(key, {f"{other}:{uuid4()}": time.time() - 1})
        assert (
            await update_presence(
                redis, workspace, conversation, actor, second, online=False
            )
            == set()
        )
        assert await redis.zcard(key) == 0
    finally:
        await redis.delete(key)
        await redis.aclose()


async def test_customer_cannot_observe_another_visitors_presence(client):
    identity = (await client.post("/api/v1/public/demo")).json()
    workspace = UUID(identity["workspace_id"])
    async with Session.begin() as db:
        other = Actor(
            id=uuid4(),
            workspace_id=workspace,
            kind="visitor",
            display_name="Fictional other visitor",
        )
        db.add(other)
        await db.flush()
        conversation = await create_conversation(db, other, str(uuid4()))
        cid, actor = conversation.id, other.id
    redis = Redis.from_url(get_settings().redis_url)
    key = f"sd:presence:{workspace}:{cid}"
    try:
        await update_presence(redis, workspace, cid, actor, uuid4())
        async with api_process(18001):
            cookies = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
            async with connect(
                "ws://127.0.0.1:18001/api/v1/realtime/customer",
                origin="http://localhost:5173",
                additional_headers={"Cookie": cookies},
            ) as socket:
                await socket.send(
                    json.dumps(
                        {
                            "protocol_version": 1,
                            "type": "subscribe",
                            "conversation_id": str(cid),
                            "after_seq": 0,
                        }
                    )
                )
                async with asyncio.timeout(3):
                    with pytest.raises(ConnectionClosed):
                        while True:
                            frame = json.loads(await socket.recv())
                            assert frame["type"] == "ping"
    finally:
        await redis.delete(key)
        await redis.aclose()

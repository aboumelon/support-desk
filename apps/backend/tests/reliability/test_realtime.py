"""Real network API replicas and Redis; no eager broker substitutes."""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from redis.asyncio import Redis
from websockets.asyncio.client import connect

from supportdesk.config import get_settings
from supportdesk.workers.dispatcher import dispatch_once


@asynccontextmanager
async def api_process(port):
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "uvicorn",
        "supportdesk.main:create_app",
        "--factory",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        env=os.environ.copy(),
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        async with httpx.AsyncClient(
            base_url=f"http://127.0.0.1:{port}", trust_env=False
        ) as client:
            for _ in range(100):
                try:
                    if (await client.get("/api/v1/health/ready")).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                await asyncio.sleep(0.1)
            else:
                raise AssertionError("API did not become ready")
        yield
    finally:
        process.terminate()
        await asyncio.wait_for(process.wait(), 10)


async def next_event(socket, event_type, timeout=18):
    async with asyncio.timeout(timeout):
        while True:
            frame = json.loads(await socket.recv())
            if frame["type"] == event_type:
                return frame


async def test_two_instances_lost_final_notification_and_replay():
    origin = "http://localhost:5173"
    async with (
        api_process(18001),
        api_process(18002),
        httpx.AsyncClient(
            base_url="http://127.0.0.1:18001",
            headers={"Origin": origin},
            trust_env=False,
        ) as client,
    ):
        identity = (await client.post("/api/v1/public/demo")).json()
        client.headers["X-CSRF-Token"] = identity["csrf_token"]
        conversation = (
            await client.post(
                "/api/v1/customer/conversations",
                headers={"Idempotency-Key": str(uuid4())},
            )
        ).json()
        cid, workspace = conversation["id"], identity["workspace_id"]
        cookies = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
        url = f"ws://127.0.0.1:18002/api/v1/realtime/staff?workspace_id={workspace}"
        async with connect(
            url, origin=origin, additional_headers={"Cookie": cookies}
        ) as socket:
            await socket.send(
                json.dumps(
                    {
                        "protocol_version": 1,
                        "type": "subscribe",
                        "conversation_id": cid,
                        "after_seq": 0,
                    }
                )
            )
            assert (await next_event(socket, "conversation.created"))["seq"] == 1
            response = await client.post(
                f"/api/v1/customer/conversations/{cid}/messages",
                json={
                    "client_message_id": str(uuid4()),
                    "body": "Redis wakeup crosses API replicas",
                },
            )
            assert response.status_code == 201
            redis = Redis.from_url(get_settings().redis_url)
            try:
                while await dispatch_once(redis):
                    pass
            finally:
                await redis.aclose()
            assert (await next_event(socket, "message.created", timeout=3))["seq"] == 2
            # Skip this notification; no later event follows it.
            response = await client.post(
                f"/api/v1/customer/conversations/{cid}/messages",
                json={
                    "client_message_id": str(uuid4()),
                    "body": "Recover a lost final notification",
                },
            )
            assert response.status_code == 201
            assert (await next_event(socket, "message.created", timeout=18))["seq"] == 3
        async with connect(
            url, origin=origin, additional_headers={"Cookie": cookies}
        ) as socket:
            await socket.send(
                json.dumps(
                    {
                        "protocol_version": 1,
                        "type": "subscribe",
                        "conversation_id": cid,
                        "after_seq": 2,
                    }
                )
            )
            assert (await next_event(socket, "message.created", timeout=3))["seq"] == 3


async def test_real_redis_outage_preserves_rest_and_watermark_delivery(monkeypatch):
    import subprocess

    name = "sd-recovery-" + uuid4().hex[:10]
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-p",
            "127.0.0.1:56380:6379",
            "redis:8.0.2-alpine",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:56380/0")
    redis = Redis.from_url("redis://127.0.0.1:56380/0")
    try:
        async with asyncio.timeout(10):
            while True:
                try:
                    await redis.ping()
                    break
                except Exception:
                    await asyncio.sleep(0.1)
        origin = "http://localhost:5173"
        async with (
            api_process(18001),
            httpx.AsyncClient(
                base_url="http://127.0.0.1:18001",
                headers={"Origin": origin},
                trust_env=False,
            ) as client,
        ):
            identity = (await client.post("/api/v1/public/demo")).json()
            client.headers["X-CSRF-Token"] = identity["csrf_token"]
            conversation = (
                await client.post(
                    "/api/v1/customer/conversations",
                    headers={"Idempotency-Key": str(uuid4())},
                )
            ).json()
            cid = conversation["id"]
            cookies = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
            async with connect(
                "ws://127.0.0.1:18001/api/v1/realtime/customer",
                origin=origin,
                additional_headers={"Cookie": cookies},
            ) as socket:
                await socket.send(
                    json.dumps(
                        {
                            "protocol_version": 1,
                            "type": "subscribe",
                            "conversation_id": cid,
                            "after_seq": 1,
                        }
                    )
                )
                await next_event(socket, "ping", 3)
                subprocess.run(
                    ["docker", "stop", "-t", "0", name],
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
                response = await client.post(
                    f"/api/v1/customer/conversations/{cid}/messages",
                    json={
                        "client_message_id": str(uuid4()),
                        "body": "Human chat survives an actual Redis outage",
                    },
                )
                assert response.status_code == 201
                assert (await next_event(socket, "message.created", 18))["seq"] == 2
                assert (await client.get("/api/v1/health/ready")).json()[
                    "redis"
                ] == "degraded"
                subprocess.run(
                    ["docker", "start", name], check=True, stdout=subprocess.DEVNULL
                )
                async with asyncio.timeout(5):
                    while True:
                        try:
                            await redis.ping()
                            break
                        except Exception:
                            await asyncio.sleep(0.1)
                response = await client.post(
                    f"/api/v1/customer/conversations/{cid}/messages",
                    json={"client_message_id": str(uuid4()), "body": "Redis recovered"},
                )
                assert response.status_code == 201
                while await dispatch_once(redis):
                    pass
                assert (await next_event(socket, "message.created", 18))["seq"] == 3
    finally:
        await redis.aclose()
        subprocess.run(
            ["docker", "rm", "-f", name], check=False, stdout=subprocess.DEVNULL
        )


async def test_two_hundred_retained_events_replay_below_three_seconds(client):
    import hashlib
    import time
    from uuid import UUID

    from supportdesk.infrastructure.database import Session, now
    from supportdesk.modules.conversations.models import Conversation
    from supportdesk.modules.messaging.models import ConversationEvent, Message

    identity = (await client.post("/api/v1/public/demo")).json()
    client.headers["X-CSRF-Token"] = identity["csrf_token"]
    conversation = (
        await client.post(
            "/api/v1/customer/conversations", headers={"Idempotency-Key": str(uuid4())}
        )
    ).json()
    cid, workspace, actor = (
        UUID(conversation["id"]),
        UUID(identity["workspace_id"]),
        UUID(identity["actor_id"]),
    )
    async with Session.begin() as db:
        stored = await db.get(Conversation, cid)
        for seq in range(2, 202):
            body = f"Explicit fictional replay fixture {seq}"
            message_id = uuid4()
            db.add(
                Message(
                    id=message_id,
                    workspace_id=workspace,
                    conversation_id=cid,
                    sender_actor_id=actor,
                    sender_kind="visitor",
                    client_message_id=uuid4(),
                    body=body,
                    body_hash=hashlib.sha256(body.encode()).hexdigest(),
                    event_seq=seq,
                    created_at=now(),
                )
            )
            db.add(
                ConversationEvent(
                    workspace_id=workspace,
                    conversation_id=cid,
                    seq=seq,
                    type="message.created",
                    payload={
                        "id": str(message_id),
                        "sender_kind": "visitor",
                        "body": body,
                    },
                )
            )
        stored.last_event_seq = 201
    async with api_process(18001):
        cookies = "; ".join(f"{k}={v}" for k, v in client.cookies.items())
        async with connect(
            "ws://127.0.0.1:18001/api/v1/realtime/customer",
            origin="http://localhost:5173",
            additional_headers={"Cookie": cookies},
        ) as socket:
            start = time.perf_counter()
            await socket.send(
                json.dumps(
                    {
                        "protocol_version": 1,
                        "type": "subscribe",
                        "conversation_id": str(cid),
                        "after_seq": 1,
                    }
                )
            )
            seen = []
            async with asyncio.timeout(3):
                while len(seen) < 200:
                    event = json.loads(await socket.recv())
                    if event.get("seq"):
                        seen.append(event["seq"])
            elapsed = time.perf_counter() - start
            assert seen == list(range(2, 202))
            assert elapsed < 3

import asyncio
import contextlib
import json
import time
from uuid import UUID, uuid4

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import select

from supportdesk.api.errors import Problem
from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Session
from supportdesk.infrastructure.metrics import open_sockets
from supportdesk.modules.conversations.models import Conversation
from supportdesk.modules.conversations.service import load_conversation
from supportdesk.modules.identity.service import resolve, workspace_actor
from supportdesk.modules.messaging.models import ConversationEvent
from supportdesk.modules.realtime.protocol import (
    AiDelta,
    PresenceUpdate,
    Subscribe,
    TypingUpdate,
)

router = APIRouter()


async def serve(
    socket: WebSocket, audience: str, workspace_id: UUID | None = None
) -> None:
    settings = get_settings()
    if socket.headers.get("origin") not in settings.allowed_origins:
        await socket.close(code=1008)
        return
    request = Request({**socket.scope, "type": "http", "method": "GET"})
    try:
        async with Session.begin() as db:
            principal = await resolve(db, request, audience)
            if principal.actor:
                workspace_id = principal.actor.workspace_id
            if workspace_id is None:
                raise Problem(404, "RESOURCE_NOT_FOUND")
            await workspace_actor(db, principal, workspace_id)
    except Problem:
        await socket.close(code=1008)
        return
    await socket.accept()
    open_sockets.inc()
    subscriptions: dict[UUID, int] = {}
    queue: asyncio.Queue[str] = asyncio.Queue(maxsize=256)
    buffered_bytes = 0
    wake = asyncio.Event()
    connection_id = uuid4()
    last_typing = 0.0
    presence_keys: set[str] = set()
    known_presence: dict[UUID, set[UUID]] = {}
    redis = Redis.from_url(
        settings.redis_url, socket_connect_timeout=2, socket_timeout=3
    )

    def enqueue(frame: dict[str, object]) -> None:
        nonlocal buffered_bytes
        encoded = json.dumps(frame, ensure_ascii=False)
        size = len(encoded.encode())
        if buffered_bytes + size > 1048576 or queue.full():
            raise Problem(429, "SLOW_CONSUMER")
        queue.put_nowait(encoded)
        buffered_bytes += size

    async def sender() -> None:
        nonlocal buffered_bytes
        while True:
            frame = await queue.get()
            await asyncio.wait_for(socket.send_text(frame), timeout=5)
            buffered_bytes -= len(frame.encode())

    async def receiver() -> None:
        nonlocal last_typing
        while True:
            raw = await socket.receive_text()
            if len(raw.encode()) > 8192:
                raise Problem(422, "INVALID_FRAME")
            payload = json.loads(raw)
            if not isinstance(payload, dict) or payload.get("protocol_version") != 1:
                raise Problem(422, "UNSUPPORTED_PROTOCOL")
            if payload.get("type") == "subscribe":
                sub = Subscribe.model_validate(payload)
                if (
                    len(subscriptions) >= 20
                    and sub.conversation_id not in subscriptions
                ):
                    raise Problem(429, "SUBSCRIPTION_LIMIT")
                # DB authorization occurs before any durable delivery.
                subscriptions[sub.conversation_id] = sub.after_seq
                wake.set()
            elif payload.get("type") == "unsubscribe":
                subscriptions.pop(UUID(payload["conversation_id"]), None)
            elif payload.get("type") == "typing.updated":
                if time.monotonic() - last_typing < 1:
                    continue
                cid = UUID(payload["conversation_id"])
                if cid not in subscriptions:
                    raise Problem(403, "FORBIDDEN")
                async with Session.begin() as db:
                    principal = await resolve(db, request, audience)
                    assert workspace_id is not None
                    actor = await workspace_actor(db, principal, workspace_id)
                    await load_conversation(db, actor, cid)
                    actor_id = actor.id
                last_typing = time.monotonic()
                with contextlib.suppress(Exception):
                    await redis.publish(
                        f"sd:ephemeral:{workspace_id}",
                        TypingUpdate(
                            type="typing.updated",
                            conversation_id=cid,
                            actor_id=actor_id,
                        ).model_dump_json(),
                    )
            elif payload.get("type") == "ping":
                enqueue({"protocol_version": 1, "type": "pong"})
            elif payload.get("type") != "pong":
                raise Problem(422, "UNKNOWN_EVENT_TYPE")

    async def notifications() -> None:
        while True:
            try:
                async with redis.pubsub() as pubsub:
                    await pubsub.subscribe(
                        f"sd:workspace:{workspace_id}",
                        f"sd:draft:{workspace_id}",
                        f"sd:ephemeral:{workspace_id}",
                    )
                    wake.set()
                    while True:
                        message = await pubsub.get_message(
                            ignore_subscribe_messages=True, timeout=1
                        )
                        if message:
                            channel = message["channel"].decode()
                            if channel == f"sd:workspace:{workspace_id}":
                                if UUID(message["data"].decode()) in subscriptions:
                                    wake.set()
                                continue
                            frame = json.loads(message["data"])
                            cid = UUID(frame["conversation_id"])
                            if cid not in subscriptions:
                                continue
                            async with Session.begin() as db:
                                principal = await resolve(db, request, audience)
                                assert workspace_id is not None
                                actor = await workspace_actor(
                                    db, principal, workspace_id
                                )
                                conversation = await load_conversation(db, actor, cid)
                                epoch = conversation.control_epoch
                            if frame.get("type") == "ai.delta":
                                delta = AiDelta.model_validate(frame)
                                if delta.control_epoch == epoch:
                                    enqueue(json.loads(delta.model_dump_json()))
                            elif frame.get("type") == "typing.updated":
                                enqueue(
                                    json.loads(
                                        TypingUpdate.model_validate(
                                            frame
                                        ).model_dump_json()
                                    )
                                )
                            elif frame.get("type") == "presence.updated":
                                enqueue(
                                    json.loads(
                                        PresenceUpdate.model_validate(
                                            frame
                                        ).model_dump_json()
                                    )
                                )
            except (asyncio.CancelledError, Problem, ValidationError, ValueError):
                raise
            except Exception:
                await asyncio.sleep(1)

    async def replay() -> None:
        while True:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(wake.wait(), timeout=15)
            wake.clear()
            # Revalidate session, tenant and membership on every heartbeat.
            async with Session.begin() as db:
                principal = await resolve(db, request, audience)
                assert workspace_id is not None
                actor = await workspace_actor(db, principal, workspace_id)
                actor_id, actor_kind = actor.id, actor.kind
            for cid in list(subscriptions):
                key = f"sd:presence:{workspace_id}:{actor_id}:{connection_id}:{cid}"
                with contextlib.suppress(Exception):
                    first_seen = key not in presence_keys
                    await redis.set(key, "1", ex=30)
                    presence_keys.add(key)
                    if first_seen:
                        await redis.publish(
                            f"sd:ephemeral:{workspace_id}",
                            PresenceUpdate(
                                type="presence.updated",
                                conversation_id=cid,
                                actor_id=actor_id,
                                online=True,
                            ).model_dump_json(),
                        )
                with contextlib.suppress(Exception):
                    present = {
                        UUID(item.decode().split(":")[-3])
                        async for item in redis.scan_iter(
                            match=f"sd:presence:{workspace_id}:*:*:{cid}"
                        )
                    }
                    previous = known_presence.get(cid, set())
                    for changed_actor in present ^ previous:
                        enqueue(
                            json.loads(
                                PresenceUpdate(
                                    type="presence.updated",
                                    conversation_id=cid,
                                    actor_id=changed_actor,
                                    online=changed_actor in present,
                                ).model_dump_json()
                            )
                        )
                    known_presence[cid] = present
                while cid in subscriptions:
                    cursor = subscriptions[cid]
                    async with Session() as db:
                        # Revalidate for every page, including backlogs larger than 100.
                        principal = await resolve(db, request, audience)
                        await workspace_actor(db, principal, workspace_id)
                        query = select(Conversation).where(
                            Conversation.id == cid,
                            Conversation.workspace_id == workspace_id,
                        )
                        if actor_kind == "visitor":
                            query = query.where(
                                Conversation.visitor_actor_id == actor_id
                            )
                        conversation = await db.scalar(query)
                        if conversation is None:
                            raise Problem(404, "RESOURCE_NOT_FOUND")
                        events = (
                            await db.scalars(
                                select(ConversationEvent)
                                .where(
                                    ConversationEvent.workspace_id == workspace_id,
                                    ConversationEvent.conversation_id == cid,
                                    ConversationEvent.seq > cursor,
                                )
                                .order_by(ConversationEvent.seq)
                                .limit(100)
                            )
                        ).all()
                        high = conversation.last_event_seq
                        await db.commit()
                    if cursor > high or (
                        cursor < high and (not events or events[0].seq != cursor + 1)
                    ):
                        enqueue(
                            {
                                "protocol_version": 1,
                                "type": "RESET_REQUIRED",
                                "conversation_id": str(cid),
                            }
                        )
                        subscriptions.pop(cid, None)
                        break
                    for event in events:
                        enqueue(
                            {
                                "protocol_version": 1,
                                "type": event.type,
                                "event_id": str(event.id),
                                "conversation_id": str(cid),
                                "seq": event.seq,
                                "occurred_at": event.created_at.isoformat(),
                                "data": event.payload,
                            }
                        )
                        subscriptions[cid] = event.seq
                    if len(events) < 100:
                        break
                    await asyncio.sleep(0)
            enqueue({"protocol_version": 1, "type": "ping"})

    tasks = [
        asyncio.create_task(fn()) for fn in [sender, receiver, notifications, replay]
    ]
    try:
        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            task.result()
    except (WebSocketDisconnect, Problem, ValidationError, ValueError, TimeoutError):
        pass
    finally:
        open_sockets.dec()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        for key in presence_keys:
            with contextlib.suppress(Exception):
                await redis.delete(key)
                parts = key.split(":")
                cid = UUID(parts[-1])
                actor_id = UUID(parts[-3])
                remaining = [
                    item
                    async for item in redis.scan_iter(
                        match=f"sd:presence:{workspace_id}:{actor_id}:*:{cid}"
                    )
                ]
                await redis.publish(
                    f"sd:ephemeral:{workspace_id}",
                    PresenceUpdate(
                        type="presence.updated",
                        conversation_id=cid,
                        actor_id=actor_id,
                        online=bool(remaining),
                    ).model_dump_json(),
                )
        await redis.aclose()
        with contextlib.suppress(RuntimeError, WebSocketDisconnect):
            await socket.close(
                code=1012, reason="Reconnect and replay committed events"
            )


@router.websocket("/api/v1/realtime/customer")
async def customer(socket: WebSocket) -> None:
    await serve(socket, "visitor")


@router.websocket("/api/v1/realtime/staff")
async def staff(socket: WebSocket, workspace_id: UUID) -> None:
    await serve(socket, "staff", workspace_id)

import hashlib
import json
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.api.errors import Problem
from supportdesk.infrastructure.database import now
from supportdesk.modules.conversations.models import CommandReceipt, Conversation
from supportdesk.modules.conversations.schemas import (
    ConversationView,
    MessageInput,
    MessageView,
    SendResult,
)
from supportdesk.modules.identity.service import rate_limit
from supportdesk.modules.jobs.models import Outbox
from supportdesk.modules.messaging.models import ConversationEvent, Message
from supportdesk.modules.workspaces.models import Actor


def request_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


async def load_conversation(
    db: AsyncSession, actor: Actor, conversation_id: UUID
) -> Conversation:
    query = select(Conversation).where(
        Conversation.workspace_id == actor.workspace_id,
        Conversation.id == conversation_id,
    )
    if actor.kind == "visitor":
        query = query.where(Conversation.visitor_actor_id == actor.id)
    conversation = await db.scalar(query.with_for_update())
    if not conversation:
        raise Problem(404, "RESOURCE_NOT_FOUND")
    return conversation


async def emit(
    db: AsyncSession,
    conversation: Conversation,
    event_type: str,
    payload: dict[str, Any],
) -> ConversationEvent:
    conversation.last_event_seq += 1
    conversation.updated_at = now()
    event = ConversationEvent(
        id=uuid4(),
        workspace_id=conversation.workspace_id,
        conversation_id=conversation.id,
        seq=conversation.last_event_seq,
        type=event_type,
        payload=payload,
        created_at=now(),
    )
    db.add(event)
    db.add(
        Outbox(
            workspace_id=conversation.workspace_id,
            kind="conversation.notify",
            reference_id=conversation.id,
            dedupe_key=f"event:{event.id}",
        )
    )
    return event


async def receipt(
    db: AsyncSession, actor: Actor, operation: str, key: str, payload: dict[str, Any]
) -> dict[str, Any] | None:
    item = await db.scalar(
        select(CommandReceipt).where(
            CommandReceipt.workspace_id == actor.workspace_id,
            CommandReceipt.actor_id == actor.id,
            CommandReceipt.operation == operation,
            CommandReceipt.key == key,
        )
    )
    if item:
        if item.request_hash != request_hash(payload):
            raise Problem(409, "IDEMPOTENCY_CONFLICT")
        return item.response
    return None


def save_receipt(
    db: AsyncSession,
    actor: Actor,
    operation: str,
    key: str,
    payload: dict[str, Any],
    response: dict[str, Any],
) -> None:
    db.add(
        CommandReceipt(
            workspace_id=actor.workspace_id,
            actor_id=actor.id,
            operation=operation,
            key=key,
            request_hash=request_hash(payload),
            response=response,
        )
    )


async def create_conversation(
    db: AsyncSession, actor: Actor, key: str
) -> ConversationView:
    await db.execute(select(Actor).where(Actor.id == actor.id).with_for_update())
    prior = await receipt(db, actor, "create_conversation", key, {})
    if prior:
        return ConversationView.model_validate(prior)
    from supportdesk.modules.assistant.service import ready
    from supportdesk.modules.workspaces.models import Workspace

    workspace = await db.get(Workspace, actor.workspace_id)
    bot_ready = (
        workspace is not None
        and workspace.ai_enabled
        and await ready(db, actor.workspace_id)
    )
    conversation = Conversation(
        id=uuid4(),
        workspace_id=actor.workspace_id,
        visitor_actor_id=actor.id,
        last_event_seq=0,
        status="open",
        controller="bot" if bot_ready else "queue",
        control_epoch=0,
        state_version=1,
        updated_at=now(),
    )
    db.add(conversation)
    await db.flush()
    await emit(
        db,
        conversation,
        "conversation.created",
        {"controller": conversation.controller},
    )
    view = ConversationView.model_validate(conversation)
    save_receipt(
        db, actor, "create_conversation", key, {}, view.model_dump(mode="json")
    )
    return view


async def send(
    db: AsyncSession, actor: Actor, conversation_id: UUID, body: MessageInput
) -> tuple[SendResult, bool]:
    conversation = await load_conversation(db, actor, conversation_id)
    hashed = hashlib.sha256(body.body.encode()).hexdigest()
    prior = await db.scalar(
        select(Message).where(
            Message.conversation_id == conversation.id,
            Message.workspace_id == actor.workspace_id,
            Message.sender_actor_id == actor.id,
            Message.client_message_id == body.client_message_id,
        )
    )
    if prior:
        if prior.body_hash != hashed:
            raise Problem(409, "IDEMPOTENCY_CONFLICT")
        return SendResult(
            message=MessageView.model_validate(prior),
            conversation=ConversationView.model_validate(conversation),
        ), False
    if conversation.status != "open":
        raise Problem(409, "CONVERSATION_RESOLVED")
    if actor.kind == "staff" and (
        conversation.controller != "human" or conversation.assigned_actor_id != actor.id
    ):
        raise Problem(409, "NOT_ASSIGNED")
    await rate_limit("message", str(actor.id), 20, db=db)
    message = Message(
        id=uuid4(),
        workspace_id=actor.workspace_id,
        conversation_id=conversation.id,
        sender_actor_id=actor.id,
        sender_kind=actor.kind,
        client_message_id=body.client_message_id,
        body=body.body,
        body_hash=hashed,
        event_seq=conversation.last_event_seq + 1,
        created_at=now(),
    )
    db.add(message)
    view = MessageView.model_validate(message)
    await emit(db, conversation, "message.created", view.model_dump(mode="json"))
    if actor.kind == "visitor" and conversation.controller == "bot":
        from supportdesk.modules.assistant.service import admit, supersede

        conversation.control_epoch += 1
        await supersede(db, conversation)
        if not await admit(db, conversation, message.event_seq):
            conversation.controller = "queue"
            conversation.state_version += 1
            await emit(
                db,
                conversation,
                "conversation.control_changed",
                {
                    "controller": "queue",
                    "reason": "AI_ADMISSION_UNAVAILABLE",
                    "control_epoch": conversation.control_epoch,
                    "state_version": conversation.state_version,
                },
            )

    return SendResult(
        message=view, conversation=ConversationView.model_validate(conversation)
    ), True

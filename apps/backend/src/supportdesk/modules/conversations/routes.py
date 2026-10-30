import base64
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.api.errors import Problem
from supportdesk.infrastructure.database import get_db
from supportdesk.modules.assistant.models import AiRun, MessageCitation
from supportdesk.modules.assistant.schemas import CitationView, RunView
from supportdesk.modules.conversations.control import control
from supportdesk.modules.conversations.inbox import inbox
from supportdesk.modules.conversations.schemas import (
    ControlInput,
    ConversationView,
    MessageInput,
    MessageView,
    ReadInput,
    SendResult,
    Snapshot,
)
from supportdesk.modules.conversations.service import (
    create_conversation,
    emit,
    load_conversation,
    send,
)
from supportdesk.modules.identity.service import resolve, workspace_actor
from supportdesk.modules.knowledge.models import Document
from supportdesk.modules.messaging.models import ConversationEvent, Message, ReadCursor
from supportdesk.modules.realtime.protocol import DurableEvent
from supportdesk.modules.workspaces.models import Actor

DB = Annotated[AsyncSession, Depends(get_db)]
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]
router = APIRouter()


def audience_router(audience: str) -> APIRouter:
    prefix = (
        "/api/v1/customer"
        if audience == "visitor"
        else "/api/v1/staff/workspaces/{workspace_id}"
    )
    routes = APIRouter(prefix=prefix)

    async def authorized(
        request: Request, db: DB, workspace_id: UUID | None = None
    ) -> Actor:
        principal = await resolve(db, request, audience)
        if audience == "visitor":
            assert principal.actor is not None
            return principal.actor
        if not workspace_id:
            raise Problem(404, "RESOURCE_NOT_FOUND")
        return await workspace_actor(db, principal, workspace_id)

    Auth = Annotated[Actor, Depends(authorized)]

    @routes.get("/conversations", response_model=list[ConversationView])
    async def listing(
        response: Response,
        db: DB,
        actor: Auth,
        status: str | None = None,
        controller: str | None = None,
        assigned_actor_id: UUID | None = None,
        before: int | None = None,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        q: Annotated[str | None, Query(min_length=2, max_length=120)] = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> list[ConversationView]:
        result, next_cursor = await inbox(
            db, actor, status, controller, assigned_actor_id, before, cursor, q, limit
        )
        if next_cursor:
            response.headers["X-Next-Cursor"] = next_cursor
        await db.commit()
        return result

    @routes.get("/conversations/{conversation_id}/snapshot", response_model=Snapshot)
    async def snapshot(conversation_id: UUID, db: DB, actor: Auth) -> Snapshot:
        conversation = await load_conversation(db, actor, conversation_id)
        messages = (
            await db.scalars(
                select(Message)
                .where(
                    Message.workspace_id == actor.workspace_id,
                    Message.conversation_id == conversation_id,
                )
                .order_by(Message.event_seq.desc())
                .limit(50)
            )
        ).all()
        cursors = (
            await db.scalars(
                select(ReadCursor).where(
                    ReadCursor.workspace_id == actor.workspace_id,
                    ReadCursor.conversation_id == conversation_id,
                )
            )
        ).all()
        active_run = await db.scalar(
            select(AiRun)
            .where(
                AiRun.workspace_id == actor.workspace_id,
                AiRun.conversation_id == conversation_id,
            )
            .order_by(AiRun.created_at.desc())
            .limit(1)
        )
        result = Snapshot(
            conversation=ConversationView.model_validate(conversation),
            messages=[MessageView.model_validate(m) for m in reversed(messages)],
            event_cursor=conversation.last_event_seq,
            active_run=RunView.model_validate(active_run) if active_run else None,
            read_cursors={str(c.actor_id): c.last_read_seq for c in cursors},
        )
        await db.commit()
        return result

    @routes.post("/conversations/{conversation_id}/messages", response_model=SendResult)
    async def send_message(
        conversation_id: UUID,
        body: MessageInput,
        response: Response,
        db: DB,
        actor: Auth,
    ) -> SendResult:
        result, created = await send(db, actor, conversation_id, body)
        await db.commit()
        response.status_code = 201 if created else 200
        return result

    @routes.get(
        "/conversations/{conversation_id}/messages", response_model=list[MessageView]
    )
    async def history(
        conversation_id: UUID,
        db: DB,
        actor: Auth,
        before: str | None = None,
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
    ) -> list[MessageView]:
        await load_conversation(db, actor, conversation_id)
        query = select(Message).where(
            Message.workspace_id == actor.workspace_id,
            Message.conversation_id == conversation_id,
        )
        if before:
            try:
                sequence = int(base64.urlsafe_b64decode(before).decode())
            except (ValueError, UnicodeError) as exc:
                raise Problem(422, "INVALID_CURSOR") from exc
            query = query.where(Message.event_seq < sequence)
        items = (
            await db.scalars(query.order_by(Message.event_seq.desc()).limit(limit))
        ).all()
        result = [MessageView.model_validate(m) for m in reversed(items)]
        await db.commit()
        return result

    @routes.get(
        "/conversations/{conversation_id}/events", response_model=list[DurableEvent]
    )
    async def events(
        conversation_id: UUID,
        db: DB,
        actor: Auth,
        after_seq: Annotated[int, Query(ge=0)] = 0,
    ) -> list[DurableEvent]:
        conversation = await load_conversation(db, actor, conversation_id)
        items = (
            await db.scalars(
                select(ConversationEvent)
                .where(
                    ConversationEvent.workspace_id == actor.workspace_id,
                    ConversationEvent.conversation_id == conversation_id,
                    ConversationEvent.seq > after_seq,
                )
                .order_by(ConversationEvent.seq)
                .limit(100)
            )
        ).all()
        if after_seq > conversation.last_event_seq or (
            after_seq < conversation.last_event_seq
            and (not items or items[0].seq != after_seq + 1)
        ):
            oldest = await db.scalar(
                select(func.min(ConversationEvent.seq)).where(
                    ConversationEvent.workspace_id == actor.workspace_id,
                    ConversationEvent.conversation_id == conversation_id,
                )
            )
            raise Problem(
                409,
                "RESET_REQUIRED",
                oldest_available_seq=oldest,
                event_cursor=conversation.last_event_seq,
            )
        result = [
            DurableEvent.model_validate(
                {
                    "event_id": e.id,
                    "conversation_id": conversation_id,
                    "seq": e.seq,
                    "type": e.type,
                    "occurred_at": e.created_at,
                    "data": e.payload,
                }
            )
            for e in items
        ]
        await db.commit()
        return result

    @routes.put(
        "/conversations/{conversation_id}/read-cursor", response_model=ReadInput
    )
    async def read_cursor(
        conversation_id: UUID, body: ReadInput, db: DB, actor: Auth
    ) -> ReadInput:
        conversation = await load_conversation(db, actor, conversation_id)
        visible = await db.scalar(
            select(Message.id).where(
                Message.workspace_id == actor.workspace_id,
                Message.conversation_id == conversation_id,
                Message.event_seq == body.last_read_seq,
            )
        )
        if visible is None:
            raise Problem(422, "INVALID_READ_CURSOR")
        cursor = await db.get(ReadCursor, (conversation_id, actor.id))
        if cursor is None:
            cursor = ReadCursor(
                workspace_id=actor.workspace_id,
                conversation_id=conversation_id,
                actor_id=actor.id,
                last_read_seq=0,
            )
            db.add(cursor)
        if body.last_read_seq > cursor.last_read_seq:
            cursor.last_read_seq = body.last_read_seq
            await emit(
                db,
                conversation,
                "read_cursor.updated",
                {
                    "actor_id": str(actor.id),
                    "sender_kind": actor.kind,
                    "last_read_seq": cursor.last_read_seq,
                },
            )
        result = ReadInput(last_read_seq=cursor.last_read_seq)
        await db.commit()
        return result

    @routes.get(
        "/conversations/{conversation_id}/ai-runs/{run_id}", response_model=RunView
    )
    async def run_status(
        conversation_id: UUID, run_id: UUID, db: DB, actor: Auth
    ) -> RunView:
        await load_conversation(db, actor, conversation_id)
        run = await db.scalar(
            select(AiRun).where(
                AiRun.workspace_id == actor.workspace_id,
                AiRun.conversation_id == conversation_id,
                AiRun.id == run_id,
            )
        )
        if run is None:
            raise Problem(404, "RESOURCE_NOT_FOUND")
        result = RunView.model_validate(run)
        await db.commit()
        return result

    @routes.get(
        "/conversations/{conversation_id}/citations/{message_id}/{label}",
        response_model=CitationView,
    )
    async def citation(
        conversation_id: UUID, message_id: UUID, label: str, db: DB, actor: Auth
    ) -> CitationView:
        await load_conversation(db, actor, conversation_id)
        message = await db.scalar(
            select(Message).where(
                Message.workspace_id == actor.workspace_id,
                Message.conversation_id == conversation_id,
                Message.id == message_id,
            )
        )
        if message is None:
            raise Problem(404, "RESOURCE_NOT_FOUND")
        source = await db.get(MessageCitation, (message_id, label))
        if source is None or source.workspace_id != actor.workspace_id:
            raise Problem(404, "RESOURCE_NOT_FOUND")
        doc = await db.get(Document, source.document_id)
        if doc is None or doc.withdrawn_at:
            raise Problem(410, "SOURCE_UNAVAILABLE")
        result = CitationView.model_validate(source)
        await db.commit()
        return result

    @routes.post(
        "/conversations/{conversation_id}/{action}", response_model=ConversationView
    )
    async def change_control(
        conversation_id: UUID,
        action: Literal[
            "claim",
            "handoff",
            "release",
            "resolve",
            "reopen",
            "reassign",
            "return-to-bot",
        ],
        body: ControlInput,
        idempotency_key: Key,
        db: DB,
        actor: Auth,
    ) -> ConversationView:
        result = await control(
            db, actor, conversation_id, action, body, idempotency_key
        )
        await db.commit()
        return result

    if audience == "visitor":

        @routes.post("/conversations", response_model=ConversationView)
        async def create(db: DB, actor: Auth, idempotency_key: Key) -> ConversationView:
            result = await create_conversation(db, actor, idempotency_key)
            await db.commit()
            return result

    return routes


router.include_router(audience_router("visitor"))
router.include_router(audience_router("staff"))

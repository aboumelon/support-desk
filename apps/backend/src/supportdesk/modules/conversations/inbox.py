"""Authorized, bounded inbox read model; no generated or inferred customer identity."""

import base64
import re
from datetime import datetime
from uuid import UUID

from sqlalchemy import String, cast, func, or_, select, text, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.api.errors import Problem
from supportdesk.modules.conversations.models import Conversation
from supportdesk.modules.conversations.schemas import ConversationView
from supportdesk.modules.messaging.models import Message, ReadCursor
from supportdesk.modules.workspaces.models import Actor


def excerpt(body: str | None, length: int) -> str | None:
    if not body:
        return None
    plain = re.sub(r"!?\[([^\]]+)\]\([^)]*\)", r"\1", body)
    plain = re.sub(r"[\x00-\x1f`*_#<>]", " ", plain)
    plain = " ".join(plain.split())
    return plain[:length] + ("…" if len(plain) > length else "")


def encode_cursor(conversation: Conversation) -> str:
    value = f"{conversation.updated_at.isoformat()}|{conversation.id}"
    return base64.urlsafe_b64encode(value.encode()).decode()


async def inbox(
    db: AsyncSession,
    actor: Actor,
    status: str | None,
    controller: str | None,
    assigned: UUID | None,
    before: int | None,
    cursor: str | None,
    search: str | None,
    limit: int,
) -> tuple[list[ConversationView], str | None]:
    # A fixed statement deadline also bounds broad substring searches on a large inbox.
    await db.execute(text("SET LOCAL statement_timeout = '1500ms'"))
    query = select(Conversation).where(Conversation.workspace_id == actor.workspace_id)
    if actor.kind == "visitor":
        query = query.where(Conversation.visitor_actor_id == actor.id)
    if status:
        query = query.where(Conversation.status == status)
    if controller:
        query = query.where(Conversation.controller == controller)
    if assigned:
        query = query.where(Conversation.assigned_actor_id == assigned)
    if search:
        value = search.strip().lstrip("#")
        if len(value) < 2:
            raise Problem(422, "INVALID_SEARCH")
        pattern = (
            "%"
            + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        query = query.where(
            or_(
                func.replace(cast(Conversation.id, String), "-", "").ilike(
                    value.replace("-", "")
                    .replace("\\", "\\\\")
                    .replace("%", "\\%")
                    .replace("_", "\\_")
                    + "%",
                    escape="\\",
                ),
                select(Message.id)
                .where(
                    Message.workspace_id == actor.workspace_id,
                    Message.conversation_id == Conversation.id,
                    Message.body.ilike(pattern, escape="\\"),
                )
                .exists(),
            )
        )
    if cursor:
        try:
            timestamp, identity = base64.urlsafe_b64decode(cursor).decode().split("|")
            stamp = datetime.fromisoformat(timestamp)
            if stamp.tzinfo is None:
                raise ValueError()
            identifier = UUID(identity)
        except (ValueError, UnicodeError) as exc:
            raise Problem(422, "INVALID_CURSOR") from exc
        query = query.where(
            tuple_(Conversation.updated_at, Conversation.id) < tuple_(stamp, identifier)
        )
    elif before:
        from datetime import UTC

        query = query.where(
            Conversation.updated_at < datetime.fromtimestamp(before / 1000000, UTC)
        )
    items = (
        await db.scalars(
            query.order_by(
                Conversation.updated_at.desc(), Conversation.id.desc()
            ).limit(limit + 1)
        )
    ).all()
    more = len(items) > limit
    result = []
    for conversation in items[:limit]:
        messages = select(Message).where(
            Message.workspace_id == actor.workspace_id,
            Message.conversation_id == conversation.id,
        )
        first = await db.scalar(
            messages.where(Message.sender_kind == "visitor")
            .order_by(Message.event_seq)
            .limit(1)
        )
        last = await db.scalar(messages.order_by(Message.event_seq.desc()).limit(1))
        read = await db.get(ReadCursor, (conversation.id, actor.id))
        unread = await db.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.workspace_id == actor.workspace_id,
                Message.conversation_id == conversation.id,
                Message.sender_actor_id != actor.id,
                Message.event_seq > (read.last_read_seq if read else 0),
            )
        )
        view = ConversationView.model_validate(conversation)
        view.title = excerpt(first.body if first else None, 72)
        view.last_message_preview = excerpt(last.body if last else None, 120)
        view.last_message_kind = last.sender_kind if last else None
        view.unread_count = unread or 0
        result.append(view)
    return result, encode_cursor(items[limit - 1]) if more else None

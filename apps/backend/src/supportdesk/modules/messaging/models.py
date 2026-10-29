from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from supportdesk.infrastructure.database import Base, Identified, Timestamped


class Message(Identified, Timestamped, Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "event_seq", name="uq_message_sequence"),
        UniqueConstraint(
            "conversation_id",
            "sender_actor_id",
            "client_message_id",
            name="uq_message_identity",
        ),
        UniqueConstraint("workspace_id", "id", name="uq_message_workspace"),
        ForeignKeyConstraint(
            ["workspace_id", "conversation_id"],
            ["conversations.workspace_id", "conversations.id"],
        ),
        ForeignKeyConstraint(
            ["workspace_id", "sender_actor_id"],
            ["workspace_actors.workspace_id", "workspace_actors.id"],
        ),
        CheckConstraint(
            "char_length(body) BETWEEN 1 AND 8000 AND octet_length(body) <= 32768",
            name="body_size",
        ),
    )
    workspace_id: Mapped[UUID]
    conversation_id: Mapped[UUID]
    sender_actor_id: Mapped[UUID]
    sender_kind: Mapped[str]
    client_message_id: Mapped[UUID | None]
    body: Mapped[str]
    body_hash: Mapped[str]
    event_seq: Mapped[int]
    ai_run_id: Mapped[UUID | None] = mapped_column(unique=True)


class ConversationEvent(Identified, Timestamped, Base):
    __tablename__ = "conversation_events"
    __table_args__ = (
        UniqueConstraint("conversation_id", "seq", name="uq_event_sequence"),
        ForeignKeyConstraint(
            ["workspace_id", "conversation_id"],
            ["conversations.workspace_id", "conversations.id"],
        ),
    )
    workspace_id: Mapped[UUID]
    conversation_id: Mapped[UUID]
    seq: Mapped[int]
    type: Mapped[str]
    schema_version: Mapped[int] = mapped_column(default=1)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)


class ReadCursor(Base):
    __tablename__ = "read_cursors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "conversation_id"],
            ["conversations.workspace_id", "conversations.id"],
        ),
        ForeignKeyConstraint(
            ["workspace_id", "actor_id"],
            ["workspace_actors.workspace_id", "workspace_actors.id"],
        ),
    )
    workspace_id: Mapped[UUID]
    conversation_id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_id: Mapped[UUID] = mapped_column(primary_key=True)
    last_read_seq: Mapped[int]

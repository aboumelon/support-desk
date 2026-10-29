from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from supportdesk.infrastructure.database import Base, Identified, Timestamped, now


class Conversation(Identified, Timestamped, Base):
    __tablename__ = "conversations"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_conversation_workspace"),
        ForeignKeyConstraint(
            ["workspace_id", "visitor_actor_id"],
            ["workspace_actors.workspace_id", "workspace_actors.id"],
            name="fk_conversation_visitor",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "assigned_actor_id"],
            ["workspace_actors.workspace_id", "workspace_actors.id"],
            name="fk_conversation_assignee",
        ),
        CheckConstraint("status IN ('open', 'resolved')", name="status"),
        CheckConstraint("controller IN ('bot', 'queue', 'human')", name="controller"),
        CheckConstraint(
            "(controller = 'human') = (assigned_actor_id IS NOT NULL)",
            name="assignment",
        ),
    )
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    visitor_actor_id: Mapped[UUID]
    status: Mapped[str] = mapped_column(default="open")
    controller: Mapped[str] = mapped_column(default="queue")
    assigned_actor_id: Mapped[UUID | None]
    control_epoch: Mapped[int] = mapped_column(default=0)
    state_version: Mapped[int] = mapped_column(default=1)
    last_event_seq: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=now, index=True
    )


class CommandReceipt(Identified, Timestamped, Base):
    __tablename__ = "command_receipts"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "actor_id", "operation", "key", name="uq_command_identity"
        ),
        ForeignKeyConstraint(
            ["workspace_id", "actor_id"],
            ["workspace_actors.workspace_id", "workspace_actors.id"],
        ),
    )
    workspace_id: Mapped[UUID]
    actor_id: Mapped[UUID]
    operation: Mapped[str]
    key: Mapped[str]
    request_hash: Mapped[str]
    response: Mapped[dict[str, Any]] = mapped_column(JSONB)

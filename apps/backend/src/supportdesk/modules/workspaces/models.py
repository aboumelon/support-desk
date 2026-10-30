from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from supportdesk.infrastructure.database import Base, Identified, Timestamped


class Workspace(Identified, Timestamped, Base):
    __tablename__ = "workspaces"
    public_key: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    ai_enabled: Mapped[bool] = mapped_column(default=False)
    fictional_data: Mapped[bool] = mapped_column(default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Actor(Identified, Timestamped, Base):
    __tablename__ = "workspace_actors"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_actor_workspace_id"),
        UniqueConstraint("workspace_id", "user_id", name="uq_actor_workspace_user"),
        CheckConstraint(
            "(kind = 'staff' AND user_id IS NOT NULL "
            "AND role IS NOT NULL AND role IN ('admin', 'agent')) OR "
            "(kind IN ('visitor', 'assistant') AND user_id IS NULL AND role IS NULL)",
            name="kind_role",
        ),
        Index(
            "uq_workspace_assistant",
            "workspace_id",
            unique=True,
            postgresql_where=text("kind = 'assistant'"),
        ),
    )
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"))
    kind: Mapped[str]
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("staff_users.id"))
    role: Mapped[str | None]
    display_name: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    bucket_hash: Mapped[str] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(primary_key=True)
    window_start: Mapped[int] = mapped_column(primary_key=True)
    count: Mapped[int]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

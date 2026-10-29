from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from supportdesk.infrastructure.database import Base, Identified, Timestamped, now


class Outbox(Identified, Timestamped, Base):
    __tablename__ = "outbox"
    __table_args__ = (
        CheckConstraint("status IN ('pending','published')", name="status"),
    )
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"))
    kind: Mapped[str]
    reference_id: Mapped[UUID]
    dedupe_key: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(default="pending", index=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_token: Mapped[UUID | None]
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(default=0)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Job(Identified, Timestamped, Base):
    __tablename__ = "jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','retry','succeeded','failed','cancelled')",
            name="status",
        ),
        CheckConstraint("attempt BETWEEN 0 AND 3", name="attempt_budget"),
    )
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"))
    kind: Mapped[str]
    resource_id: Mapped[UUID]
    logical_key: Mapped[str] = mapped_column(unique=True)
    status: Mapped[str] = mapped_column(default="pending", index=True)
    attempt: Mapped[int] = mapped_column(default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    lease_token: Mapped[UUID | None]
    leased_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dispatch_generation: Mapped[int] = mapped_column(default=0)
    last_dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_code: Mapped[str | None]

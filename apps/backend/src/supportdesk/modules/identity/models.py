from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from supportdesk.infrastructure.database import Base, Identified, Timestamped


class StaffUser(Identified, Timestamped, Base):
    __tablename__ = "staff_users"
    normalized_email: Mapped[str] = mapped_column(String(254), unique=True)
    password_hash: Mapped[str]
    active: Mapped[bool] = mapped_column(default=True)


class LoginSession(Identified, Base):
    __tablename__ = "sessions"
    __table_args__ = (
        CheckConstraint(
            "(staff_user_id IS NULL) <> (visitor_actor_id IS NULL)", name="one_owner"
        ),
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    staff_user_id: Mapped[UUID | None] = mapped_column(ForeignKey("staff_users.id"))
    visitor_actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workspace_actors.id")
    )
    csrf_secret: Mapped[str]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

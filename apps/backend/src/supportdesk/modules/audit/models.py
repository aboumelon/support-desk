from uuid import UUID

from sqlalchemy import ForeignKeyConstraint
from sqlalchemy.orm import Mapped

from supportdesk.infrastructure.database import Base, Identified, Timestamped


class AuditRecord(Identified, Timestamped, Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "actor_id"],
            ["workspace_actors.workspace_id", "workspace_actors.id"],
        ),
    )
    workspace_id: Mapped[UUID]
    actor_id: Mapped[UUID]
    action: Mapped[str]
    subject_id: Mapped[UUID]

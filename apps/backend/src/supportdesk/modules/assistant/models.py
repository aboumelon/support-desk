from datetime import date, datetime
from uuid import UUID

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from supportdesk.infrastructure.database import Base, Identified, Timestamped


class AiRun(Identified, Timestamped, Base):
    __tablename__ = "ai_runs"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_run_workspace"),
        UniqueConstraint(
            "conversation_id", "expected_control_epoch", name="uq_run_epoch"
        ),
        ForeignKeyConstraint(
            ["workspace_id", "conversation_id"],
            ["conversations.workspace_id", "conversations.id"],
        ),
    )
    workspace_id: Mapped[UUID]
    conversation_id: Mapped[UUID]
    trigger_message_seq: Mapped[int]
    expected_control_epoch: Mapped[int]
    status: Mapped[str] = mapped_column(default="queued")
    prompt_version: Mapped[str] = mapped_column(default="answer-v1")
    provider_model: Mapped[str]
    job_id: Mapped[UUID] = mapped_column(ForeignKey("jobs.id"))
    period: Mapped[date] = mapped_column(Date)
    per_attempt_tokens: Mapped[int]
    error_code: Mapped[str | None]
    output_message_id: Mapped[UUID | None]
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UsagePeriod(Base):
    __tablename__ = "usage_periods"
    workspace_id: Mapped[UUID] = mapped_column(
        ForeignKey("workspaces.id"), primary_key=True
    )
    period: Mapped[date] = mapped_column(Date, primary_key=True)
    charged_tokens: Mapped[int] = mapped_column(default=0)


class UsageReservation(Identified, Base):
    __tablename__ = "usage_reservations"
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"))
    ai_run_id: Mapped[UUID] = mapped_column(ForeignKey("ai_runs.id"), unique=True)
    reserved_tokens: Mapped[int]
    charged_tokens: Mapped[int]
    state: Mapped[str] = mapped_column(default="reserved")


class AiAttempt(Identified, Timestamped, Base):
    __tablename__ = "ai_attempts"
    __table_args__ = (UniqueConstraint("run_id", "attempt", name="uq_run_attempt"),)
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"))
    run_id: Mapped[UUID] = mapped_column(ForeignKey("ai_runs.id"))
    attempt: Mapped[int]
    input_tokens: Mapped[int | None]
    output_tokens: Mapped[int | None]
    usage_state: Mapped[str] = mapped_column(default="unknown")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RunSource(Base):
    __tablename__ = "run_sources"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "run_id"], ["ai_runs.workspace_id", "ai_runs.id"]
        ),
        ForeignKeyConstraint(
            ["workspace_id", "chunk_id"],
            ["knowledge_chunks.workspace_id", "knowledge_chunks.id"],
        ),
        ForeignKeyConstraint(
            ["workspace_id", "version_id"],
            ["document_versions.workspace_id", "document_versions.id"],
        ),
    )
    workspace_id: Mapped[UUID]
    run_id: Mapped[UUID] = mapped_column(primary_key=True)
    source_label: Mapped[str] = mapped_column(primary_key=True)
    chunk_id: Mapped[UUID | None]
    version_id: Mapped[UUID]
    document_id: Mapped[UUID]
    title: Mapped[str]
    excerpt: Mapped[str]
    locator: Mapped[str]


class MessageCitation(Base):
    __tablename__ = "message_citations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["workspace_id", "message_id"], ["messages.workspace_id", "messages.id"]
        ),
        ForeignKeyConstraint(
            ["workspace_id", "version_id"],
            ["document_versions.workspace_id", "document_versions.id"],
        ),
    )
    workspace_id: Mapped[UUID]
    message_id: Mapped[UUID] = mapped_column(primary_key=True)
    source_label: Mapped[str] = mapped_column(primary_key=True)
    version_id: Mapped[UUID]
    chunk_id: Mapped[UUID | None]
    document_id: Mapped[UUID]
    title: Mapped[str]
    excerpt: Mapped[str]
    locator: Mapped[str]

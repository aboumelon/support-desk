from datetime import datetime
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from supportdesk.infrastructure.database import Base, Identified, Timestamped


class Artifact(Identified, Timestamped, Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_artifact_workspace"),
    )
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"))
    storage_key: Mapped[str] = mapped_column(unique=True)
    sha256: Mapped[str]
    content_type: Mapped[str]
    bytes: Mapped[int]
    state: Mapped[str] = mapped_column(default="ready")


class Document(Identified, Timestamped, Base):
    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_document_workspace"),
        ForeignKeyConstraint(
            ["workspace_id", "active_version_id"],
            ["document_versions.workspace_id", "document_versions.id"],
            use_alter=True,
            name="fk_document_active_version",
        ),
    )
    workspace_id: Mapped[UUID] = mapped_column(ForeignKey("workspaces.id"), index=True)
    title: Mapped[str]
    active_version_id: Mapped[UUID | None]
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DocumentVersion(Identified, Timestamped, Base):
    __tablename__ = "document_versions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_version_workspace"),
        UniqueConstraint("document_id", "version_no", name="uq_document_version"),
        ForeignKeyConstraint(
            ["workspace_id", "document_id"], ["documents.workspace_id", "documents.id"]
        ),
        ForeignKeyConstraint(
            ["workspace_id", "artifact_id"], ["artifacts.workspace_id", "artifacts.id"]
        ),
        CheckConstraint(
            "status IN ('pending','processing','ready','failed','withdrawn')",
            name="status",
        ),
    )
    workspace_id: Mapped[UUID]
    document_id: Mapped[UUID]
    artifact_id: Mapped[UUID]
    version_no: Mapped[int]
    status: Mapped[str] = mapped_column(default="pending")
    parser_version: Mapped[str] = mapped_column(default="text-v1")
    embedding_model: Mapped[str]
    embedding_revision: Mapped[str]
    content_hash: Mapped[str]
    error_code: Mapped[str | None]


class KnowledgeChunk(Identified, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_chunk_workspace"),
        UniqueConstraint("version_id", "ordinal", name="uq_chunk_ordinal"),
        ForeignKeyConstraint(
            ["workspace_id", "version_id"],
            ["document_versions.workspace_id", "document_versions.id"],
        ),
    )
    workspace_id: Mapped[UUID]
    version_id: Mapped[UUID]
    ordinal: Mapped[int]
    text: Mapped[str]
    page_start: Mapped[int]
    page_end: Mapped[int]
    heading_path: Mapped[str]
    token_count: Mapped[int]
    embedding: Mapped[list[float]] = mapped_column(Vector(384))

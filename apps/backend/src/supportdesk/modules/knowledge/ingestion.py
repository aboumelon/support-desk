import hashlib
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import now
from supportdesk.infrastructure.worker_database import worker_engine
from supportdesk.modules.assistant.embeddings.e5 import encode, model
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.jobs.service import owns
from supportdesk.modules.knowledge.chunking import chunks
from supportdesk.modules.knowledge.models import (
    Artifact,
    Document,
    DocumentVersion,
    KnowledgeChunk,
)
from supportdesk.modules.knowledge.parsers import InvalidDocument, parse
from supportdesk.modules.workspaces.models import Workspace


def ingest(job_id: UUID, token: UUID) -> None:
    with Session(worker_engine()) as db, db.begin():
        job = db.get(Job, job_id)
        if job is None or not owns(job, token):
            return
        version = db.get(DocumentVersion, job.resource_id)
        if version is None:
            raise InvalidDocument("RESOURCE_NOT_FOUND")
        document = db.scalar(
            select(Document).where(Document.id == version.document_id).with_for_update()
        )
        version = db.scalar(
            select(DocumentVersion)
            .where(DocumentVersion.id == version.id)
            .with_for_update()
        )
        assert version is not None
        artifact = db.get(Artifact, version.artifact_id)
        if document is None or document.withdrawn_at or version.status == "withdrawn":
            job.status = "cancelled"
            return
        if artifact is None or artifact.workspace_id != job.workspace_id:
            raise InvalidDocument("ARTIFACT_UNAVAILABLE")
        path = get_settings().storage_root / artifact.storage_key
        content_type, expected_hash = artifact.content_type, artifact.sha256
        version_id, document_id, workspace_id = (
            version.id,
            document.id,
            job.workspace_id,
        )
        version.status = "processing"
    # All extraction, model loading and inference happen without a DB transaction.
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_hash:
        raise InvalidDocument("ARTIFACT_HASH_MISMATCH")
    pieces = chunks(parse(path, content_type), model().tokenizer)
    vectors = encode([piece.text for piece in pieces])
    with Session(worker_engine()) as db, db.begin():
        document = db.scalar(
            select(Document)
            .where(Document.id == document_id, Document.workspace_id == workspace_id)
            .with_for_update()
        )
        version = db.scalar(
            select(DocumentVersion)
            .where(
                DocumentVersion.id == version_id,
                DocumentVersion.workspace_id == workspace_id,
            )
            .with_for_update()
        )
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        workspace = db.get(Workspace, workspace_id)
        if job is None or not owns(job, token):
            return
        if (
            document is None
            or version is None
            or document.withdrawn_at
            or version.status == "withdrawn"
            or workspace is None
            or (workspace.expires_at and workspace.expires_at <= now())
        ):
            job.status = "cancelled"
            return
        for ordinal, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
            db.add(
                KnowledgeChunk(
                    workspace_id=workspace_id,
                    version_id=version_id,
                    ordinal=ordinal,
                    text=piece.text,
                    page_start=piece.page,
                    page_end=piece.page,
                    heading_path=piece.heading,
                    token_count=piece.token_count,
                    embedding=vector,
                )
            )
        version.status = "ready"
        active = (
            db.get(DocumentVersion, document.active_version_id)
            if document.active_version_id
            else None
        )
        if active is None or active.version_no < version.version_no:
            document.active_version_id = version.id
        job.status = "succeeded"
        job.leased_until = None

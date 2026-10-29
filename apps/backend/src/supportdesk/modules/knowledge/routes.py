import hashlib
import os
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Header, Request, UploadFile
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.api.errors import Problem
from supportdesk.config import get_settings
from supportdesk.infrastructure.database import get_db, now
from supportdesk.modules.assistant.schemas import AssistantSetting
from supportdesk.modules.audit.models import AuditRecord
from supportdesk.modules.conversations.service import receipt, save_receipt
from supportdesk.modules.identity.service import rate_limit, resolve, workspace_actor
from supportdesk.modules.jobs.models import Job, Outbox
from supportdesk.modules.jobs.service import enqueue
from supportdesk.modules.knowledge.models import Artifact, Document, DocumentVersion
from supportdesk.modules.knowledge.schemas import (
    DocumentView,
    JobView,
    UploadResult,
    VersionView,
)
from supportdesk.modules.workspaces.models import Actor

router = APIRouter(prefix="/api/v1/staff/workspaces/{workspace_id}")
DB = Annotated[AsyncSession, Depends(get_db)]
Key = Annotated[str, Header(alias="Idempotency-Key", min_length=1, max_length=128)]


async def admin(workspace_id: UUID, request: Request, db: DB) -> Actor:
    actor = await workspace_actor(db, await resolve(db, request, "staff"), workspace_id)
    if actor.role != "admin":
        raise Problem(403, "FORBIDDEN")
    return actor


Admin = Annotated[Actor, Depends(admin)]


@router.get("/knowledge/documents", response_model=list[DocumentView])
async def listing(db: DB, actor: Admin) -> list[DocumentView]:
    docs = (
        await db.scalars(
            select(Document)
            .where(Document.workspace_id == actor.workspace_id)
            .order_by(Document.created_at.desc())
            .limit(100)
        )
    ).all()
    result = []
    for doc in docs:
        versions = (
            await db.scalars(
                select(DocumentVersion)
                .where(
                    DocumentVersion.workspace_id == actor.workspace_id,
                    DocumentVersion.document_id == doc.id,
                )
                .order_by(DocumentVersion.version_no.desc())
            )
        ).all()
        result.append(
            DocumentView(
                id=doc.id,
                title=doc.title,
                active_version_id=doc.active_version_id,
                withdrawn_at=doc.withdrawn_at,
                versions=[VersionView.model_validate(v) for v in versions],
            )
        )
    await db.commit()
    return result


async def save_upload(file: UploadFile) -> tuple[str, str, str, int]:
    extension = Path(file.filename or "").suffix.lower()
    mime = {
        ".pdf": "application/pdf",
        ".md": "text/markdown",
        ".txt": "text/plain",
    }.get(extension)
    if mime is None or file.content_type not in {
        mime,
        "application/octet-stream",
        "text/plain",
    }:
        raise Problem(422, "UNSUPPORTED_DOCUMENT")
    root = get_settings().storage_root
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = str(uuid4())
    temp = root / f"{key}.partial"
    digest = hashlib.sha256()
    size = 0
    try:
        with temp.open("xb") as output:
            os.chmod(temp, 0o600)
            while data := await file.read(65536):
                size += len(data)
                if size > 10 * 1024 * 1024:
                    raise Problem(413, "FILE_TOO_LARGE")
                if (
                    size == len(data)
                    and mime == "application/pdf"
                    and not data.startswith(b"%PDF-")
                ):
                    raise Problem(422, "INVALID_PDF")
                digest.update(data)
                output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, root / key)
    finally:
        temp.unlink(missing_ok=True)
    return key, digest.hexdigest(), mime, size


async def upload(
    db: AsyncSession,
    actor: Actor,
    request: Request,
    file: UploadFile,
    title: str,
    key: str,
    document_id: UUID | None = None,
) -> UploadResult:
    if not title.strip() or len(title) > 200:
        raise Problem(422, "INVALID_TITLE")
    await db.commit()
    storage_key, digest, mime, size = await save_upload(file)
    try:
        await resolve(db, request, "staff")
        await db.execute(select(Actor).where(Actor.id == actor.id).with_for_update())
        operation = f"upload:{document_id or 'new'}"
        payload = {"title": title, "hash": digest}
        prior = await receipt(db, actor, operation, key, payload)
        if prior:
            (get_settings().storage_root / storage_key).unlink(missing_ok=True)
            return UploadResult.model_validate(prior)
        await rate_limit("upload", str(actor.workspace_id), 10, 3600, db=db)
        if document_id:
            doc = await db.scalar(
                select(Document)
                .where(
                    Document.id == document_id,
                    Document.workspace_id == actor.workspace_id,
                )
                .with_for_update()
            )
            if not doc or doc.withdrawn_at:
                raise Problem(404, "RESOURCE_NOT_FOUND")
        else:
            doc = Document(id=uuid4(), workspace_id=actor.workspace_id, title=title)
            db.add(doc)
            await db.flush()
        number = (
            await db.scalar(
                select(func.max(DocumentVersion.version_no)).where(
                    DocumentVersion.workspace_id == actor.workspace_id,
                    DocumentVersion.document_id == doc.id,
                )
            )
            or 0
        ) + 1
        artifact = Artifact(
            id=uuid4(),
            workspace_id=actor.workspace_id,
            storage_key=storage_key,
            sha256=digest,
            content_type=mime,
            bytes=size,
        )
        db.add(artifact)
        await db.flush()
        settings = get_settings()
        version = DocumentVersion(
            id=uuid4(),
            workspace_id=actor.workspace_id,
            document_id=doc.id,
            artifact_id=artifact.id,
            version_no=number,
            embedding_model=settings.embedding_model,
            embedding_revision=settings.embedding_revision,
            content_hash=digest,
        )
        db.add(version)
        job = enqueue(db.sync_session, actor.workspace_id, "ingestion", version.id)
        result = UploadResult(document_id=doc.id, version_id=version.id, job_id=job.id)
        save_receipt(db, actor, operation, key, payload, result.model_dump(mode="json"))
        db.add(
            AuditRecord(
                workspace_id=actor.workspace_id,
                actor_id=actor.id,
                action="knowledge.upload",
                subject_id=doc.id,
            )
        )
        await db.flush()
        return result
    except Exception:
        # Complete orphan files are removed by the maintenance command.
        raise


@router.post("/knowledge/documents", response_model=UploadResult, status_code=202)
async def create_document(
    request: Request,
    db: DB,
    actor: Admin,
    idempotency_key: Key,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
) -> UploadResult:
    result = await upload(db, actor, request, file, title, idempotency_key)
    await db.commit()
    return result


@router.post(
    "/knowledge/documents/{document_id}/versions",
    response_model=UploadResult,
    status_code=202,
)
async def replace_document(
    document_id: UUID,
    request: Request,
    db: DB,
    actor: Admin,
    idempotency_key: Key,
    file: Annotated[UploadFile, File()],
    title: Annotated[str, Form()],
) -> UploadResult:
    result = await upload(db, actor, request, file, title, idempotency_key, document_id)
    await db.commit()
    return result


@router.delete("/knowledge/documents/{document_id}", status_code=204)
async def withdraw(document_id: UUID, db: DB, actor: Admin) -> None:
    doc = await db.scalar(
        select(Document)
        .where(Document.id == document_id, Document.workspace_id == actor.workspace_id)
        .with_for_update()
    )
    if doc is None:
        raise Problem(404, "RESOURCE_NOT_FOUND")
    doc.withdrawn_at = now()
    doc.active_version_id = None
    await db.execute(
        update(DocumentVersion)
        .where(
            DocumentVersion.workspace_id == actor.workspace_id,
            DocumentVersion.document_id == document_id,
        )
        .values(status="withdrawn")
    )
    db.add(
        AuditRecord(
            workspace_id=actor.workspace_id,
            actor_id=actor.id,
            action="knowledge.withdraw",
            subject_id=doc.id,
        )
    )
    await db.commit()


@router.get("/jobs/{job_id}", response_model=JobView)
async def job_details(job_id: UUID, db: DB, actor: Admin) -> JobView:
    job = await db.scalar(
        select(Job).where(Job.id == job_id, Job.workspace_id == actor.workspace_id)
    )
    if job is None:
        raise Problem(404, "RESOURCE_NOT_FOUND")
    result = JobView.model_validate(job)
    await db.commit()
    return result


@router.post("/jobs/{job_id}/retry", response_model=JobView)
async def retry(job_id: UUID, db: DB, actor: Admin) -> JobView:
    info = await db.scalar(
        select(Job).where(Job.id == job_id, Job.workspace_id == actor.workspace_id)
    )
    if info is None:
        raise Problem(404, "RESOURCE_NOT_FOUND")
    if info.kind != "ingestion":
        raise Problem(409, "INVALID_TRANSITION")
    version = await db.get(DocumentVersion, info.resource_id)
    if version:
        doc = await db.scalar(
            select(Document)
            .where(
                Document.id == version.document_id,
                Document.workspace_id == actor.workspace_id,
            )
            .with_for_update()
        )
        if not doc or doc.withdrawn_at:
            raise Problem(409, "INVALID_TRANSITION")
    job = await db.scalar(select(Job).where(Job.id == job_id).with_for_update())
    if job is None or job.status != "failed":
        raise Problem(409, "INVALID_TRANSITION")
    job.status, job.attempt, job.error_code = "pending", 0, None
    job.available_at, job.leased_until = now(), None
    job.dispatch_generation += 1
    db.add(
        Outbox(
            workspace_id=actor.workspace_id,
            kind="job.dispatch",
            reference_id=job.id,
            dedupe_key=f"job:{job.id}:{job.dispatch_generation}",
        )
    )
    db.add(
        AuditRecord(
            workspace_id=actor.workspace_id,
            actor_id=actor.id,
            action="job.retry",
            subject_id=job.id,
        )
    )
    result = JobView.model_validate(job)
    await db.commit()
    return result


@router.put("/assistant", response_model=AssistantSetting)
async def configure_assistant(
    body: AssistantSetting, db: DB, actor: Admin
) -> AssistantSetting:
    from supportdesk.modules.assistant.service import ready
    from supportdesk.modules.workspaces.models import Workspace

    if body.enabled and not await ready(db, actor.workspace_id):
        raise Problem(409, "ASSISTANT_UNAVAILABLE")
    workspace = await db.get(Workspace, actor.workspace_id)
    assert workspace is not None
    workspace.ai_enabled = body.enabled
    db.add(
        AuditRecord(
            workspace_id=actor.workspace_id,
            actor_id=actor.id,
            action="assistant.configure",
            subject_id=workspace.id,
        )
    )
    await db.commit()
    return body

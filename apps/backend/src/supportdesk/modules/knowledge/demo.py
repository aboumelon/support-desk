import hashlib
import shutil
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.cli.seed_knowledge import FIXTURES
from supportdesk.config import get_settings
from supportdesk.modules.knowledge.models import (
    Artifact,
    Document,
    DocumentVersion,
    KnowledgeChunk,
)
from supportdesk.modules.workspaces.models import Workspace


async def clone_fictional_knowledge(db: AsyncSession, destination: Workspace) -> None:
    source = await db.scalar(
        select(Workspace).where(Workspace.public_key == "naran-demo")
    )
    if source is None:
        return
    for path in sorted(FIXTURES.glob("*.md")):
        title = f"Fictional fixture: {path.stem}"
        row = (
            await db.execute(
                select(Document, DocumentVersion, Artifact)
                .join(DocumentVersion, Document.active_version_id == DocumentVersion.id)
                .join(Artifact, DocumentVersion.artifact_id == Artifact.id)
                .where(
                    Document.workspace_id == source.id,
                    Document.title == title,
                    Document.withdrawn_at.is_(None),
                    DocumentVersion.status == "ready",
                )
            )
        ).first()
        if row is None:
            continue
        _, version, artifact = row
        # Never copy an administrator's replacement text into a public demo.
        if version.content_hash != hashlib.sha256(path.read_bytes()).hexdigest():
            continue
        storage_key = str(uuid4())
        shutil.copyfile(path, get_settings().storage_root / storage_key)
        copy = Artifact(
            id=uuid4(),
            workspace_id=destination.id,
            storage_key=storage_key,
            sha256=artifact.sha256,
            content_type=artifact.content_type,
            bytes=artifact.bytes,
        )
        doc = Document(id=uuid4(), workspace_id=destination.id, title=title)
        db.add_all([copy, doc])
        await db.flush()
        active = DocumentVersion(
            id=uuid4(),
            workspace_id=destination.id,
            document_id=doc.id,
            artifact_id=copy.id,
            version_no=1,
            status="ready",
            embedding_model=version.embedding_model,
            embedding_revision=version.embedding_revision,
            content_hash=version.content_hash,
        )
        db.add(active)
        await db.flush()
        doc.active_version_id = active.id
        for chunk in (
            await db.scalars(
                select(KnowledgeChunk).where(
                    KnowledgeChunk.workspace_id == source.id,
                    KnowledgeChunk.version_id == version.id,
                )
            )
        ).all():
            db.add(
                KnowledgeChunk(
                    workspace_id=destination.id,
                    version_id=active.id,
                    ordinal=chunk.ordinal,
                    text=chunk.text,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    heading_path=chunk.heading_path,
                    token_count=chunk.token_count,
                    embedding=chunk.embedding,
                )
            )
        destination.ai_enabled = True

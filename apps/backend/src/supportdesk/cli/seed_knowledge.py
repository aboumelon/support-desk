"""Seed only versioned, explicitly fictional knowledge documents."""

import asyncio
import hashlib
import shutil
from uuid import uuid4

from sqlalchemy import select

from supportdesk.config import get_settings, project_root
from supportdesk.infrastructure.database import Session
from supportdesk.modules.jobs.service import enqueue
from supportdesk.modules.knowledge.models import Artifact, Document, DocumentVersion
from supportdesk.modules.workspaces.models import Workspace

FIXTURES = project_root() / "evals" / "rag" / "fixtures"


async def seed() -> None:
    settings = get_settings()
    if settings.app_env == "production":
        raise RuntimeError("Fictional fixtures require a development profile")
    settings.storage_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    async with Session.begin() as db:
        workspace = await db.scalar(
            select(Workspace).where(Workspace.public_key == "naran-demo")
        )
        if workspace is None:
            raise RuntimeError("Run seed_demo first")
        for path in sorted(FIXTURES.glob("*.md")):
            title = f"Fictional fixture: {path.stem}"
            if await db.scalar(
                select(Document.id).where(
                    Document.workspace_id == workspace.id, Document.title == title
                )
            ):
                continue
            key = str(uuid4())
            shutil.copyfile(path, settings.storage_root / key)
            artifact = Artifact(
                id=uuid4(),
                workspace_id=workspace.id,
                storage_key=key,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                content_type="text/markdown",
                bytes=path.stat().st_size,
            )
            doc = Document(id=uuid4(), workspace_id=workspace.id, title=title)
            db.add_all([artifact, doc])
            await db.flush()
            version = DocumentVersion(
                id=uuid4(),
                workspace_id=workspace.id,
                document_id=doc.id,
                artifact_id=artifact.id,
                version_no=1,
                embedding_model=settings.embedding_model,
                embedding_revision=settings.embedding_revision,
                content_hash=artifact.sha256,
            )
            db.add(version)
            enqueue(db.sync_session, workspace.id, "ingestion", version.id)
    print("Five fictional knowledge documents queued for ingestion")


if __name__ == "__main__":
    asyncio.run(seed())

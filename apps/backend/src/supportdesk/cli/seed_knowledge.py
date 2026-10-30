"""Seed only versioned, explicitly fictional knowledge documents."""

import asyncio
import hashlib
import shutil
from uuid import uuid4

from sqlalchemy import func, select

from supportdesk.config import get_settings, project_root
from supportdesk.infrastructure.database import Session
from supportdesk.modules.jobs.service import enqueue
from supportdesk.modules.knowledge.models import Artifact, Document, DocumentVersion
from supportdesk.modules.workspaces.models import Workspace

FIXTURES = project_root() / "evals" / "rag" / "fixtures"


async def seed(portfolio_template: bool = False) -> None:
    settings = get_settings()
    if settings.app_env == "production" and not portfolio_template:
        raise RuntimeError("Fictional fixtures require a development profile")
    settings.storage_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    async with Session.begin() as db:
        workspace = await db.scalar(
            select(Workspace).where(Workspace.public_key == "tarvio-demo")
        )
        if workspace is None:
            raise RuntimeError("Run seed_demo first")
        if not workspace.fictional_data:
            raise RuntimeError("Refusing to change a non-fictional workspace")
        for path in sorted(FIXTURES.glob("*.md")):
            title = f"Fictional fixture: {path.stem}"
            existing = await db.scalar(
                select(Document).where(
                    Document.workspace_id == workspace.id, Document.title == title
                )
            )
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if existing and await db.scalar(
                select(DocumentVersion.id).where(
                    DocumentVersion.document_id == existing.id,
                    DocumentVersion.content_hash == digest,
                    DocumentVersion.status.in_(["pending", "processing", "ready"]),
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
            doc = existing or Document(
                id=uuid4(), workspace_id=workspace.id, title=title
            )
            db.add_all([artifact, doc])
            await db.flush()
            version = DocumentVersion(
                id=uuid4(),
                workspace_id=workspace.id,
                document_id=doc.id,
                artifact_id=artifact.id,
                version_no=(
                    await db.scalar(
                        select(func.max(DocumentVersion.version_no)).where(
                            DocumentVersion.document_id == doc.id
                        )
                    )
                    or 0
                )
                + 1,
                embedding_model=settings.embedding_model,
                embedding_revision=settings.embedding_revision,
                content_hash=artifact.sha256,
            )
            db.add(version)
            enqueue(db.sync_session, workspace.id, "ingestion", version.id)
    print("Five fictional knowledge documents queued for ingestion")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--portfolio-template", action="store_true")
    asyncio.run(seed(parser.parse_args().portfolio_template))

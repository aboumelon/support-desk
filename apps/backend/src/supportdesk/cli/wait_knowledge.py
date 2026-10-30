"""Bounded readiness for the exact fictional fixture revision, not stale active text."""

import asyncio
import hashlib

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.cli.seed_knowledge import FIXTURES
from supportdesk.infrastructure.database import Session
from supportdesk.modules.knowledge.models import Document, DocumentVersion
from supportdesk.modules.workspaces.models import Workspace


async def template_ready(db: AsyncSession) -> bool:
    expected = {
        hashlib.sha256(path.read_bytes()).hexdigest() for path in FIXTURES.glob("*.md")
    }
    ready = set(
        await db.scalars(
            select(DocumentVersion.content_hash)
            .join(Document, Document.active_version_id == DocumentVersion.id)
            .join(Workspace, Document.workspace_id == Workspace.id)
            .where(
                Workspace.public_key == "tarvio-demo",
                Workspace.fictional_data.is_(True),
                Document.withdrawn_at.is_(None),
                DocumentVersion.status == "ready",
            )
        )
    )
    return len(expected) == 5 and expected <= ready


async def wait() -> None:
    async with asyncio.timeout(180):
        while True:
            try:
                async with Session() as db:
                    if await template_ready(db):
                        print("Current five fictional knowledge documents are ready")
                        return
            except (SQLAlchemyError, OSError):
                pass
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(wait())

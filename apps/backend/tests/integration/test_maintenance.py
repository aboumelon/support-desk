import asyncio
from datetime import timedelta
from uuid import UUID

from httpx import AsyncClient
from sqlalchemy import select

from supportdesk.cli.purge_expired import main
from supportdesk.infrastructure.database import Session, now
from supportdesk.modules.identity.models import LoginSession, StaffUser
from supportdesk.modules.workspaces.models import Workspace


async def test_expired_demo_is_inaccessible_and_can_be_purged(client: AsyncClient):
    identity = (await client.post("/api/v1/public/demo")).json()
    async with Session.begin() as db:
        workspace = await db.get(Workspace, UUID(identity["workspace_id"]))
        workspace.expires_at = now() - timedelta(seconds=1)
    assert (await client.get("/api/v1/customer/session")).status_code == 404
    await asyncio.to_thread(main)
    async with Session() as db:
        assert await db.scalar(select(Workspace.id)) is None
        assert await db.scalar(select(StaffUser.id)) is None
        assert await db.scalar(select(LoginSession.id)) is None


async def test_retention_preserves_recent_message_and_citation_tombstone(
    client: AsyncClient,
):
    from sqlalchemy import func

    from supportdesk.modules.assistant.models import MessageCitation, RunSource
    from supportdesk.modules.knowledge.models import (
        Document,
        DocumentVersion,
        KnowledgeChunk,
    )
    from supportdesk.modules.messaging.models import ConversationEvent, Message
    from supportdesk.workers.tasks import execute_job

    from .test_assistant import prepare

    _, _, original, jid = await prepare(client)
    await asyncio.to_thread(execute_job, jid)
    async with Session.begin() as db:
        customer = await db.scalar(
            select(Message).where(Message.sender_kind == "visitor")
        )
        customer.created_at = now() - timedelta(days=91)
        document = await db.get(Document, UUID(original["document_id"]))
        document.withdrawn_at = now() - timedelta(days=31)
        document.active_version_id = None
        version = await db.get(DocumentVersion, UUID(original["version_id"]))
        version.status = "withdrawn"
        for event in (await db.scalars(select(ConversationEvent))).all():
            event.created_at = now() - timedelta(days=31)
    await asyncio.to_thread(main)
    async with Session() as db:
        assert await db.scalar(select(func.count()).select_from(Message)) == 1
        assert await db.scalar(select(func.count()).select_from(ConversationEvent)) == 0
        assert await db.scalar(select(func.count()).select_from(KnowledgeChunk)) == 0
        citation = await db.scalar(select(MessageCitation))
        assert citation is not None and citation.chunk_id is None
        assert citation.excerpt and citation.version_id == UUID(original["version_id"])
        source = await db.scalar(select(RunSource))
        assert source.chunk_id is None
        assert await db.get(DocumentVersion, UUID(original["version_id"])) is not None

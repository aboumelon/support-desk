"""Explicit maintenance: expire demo workspaces and collect unreferenced local files."""

from datetime import timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import Base, now
from supportdesk.infrastructure.worker_database import worker_engine
from supportdesk.main import create_app
from supportdesk.modules.assistant.models import AiRun, MessageCitation, RunSource
from supportdesk.modules.audit.models import AuditRecord
from supportdesk.modules.conversations.models import CommandReceipt
from supportdesk.modules.identity.models import LoginSession
from supportdesk.modules.jobs.models import Job, Outbox
from supportdesk.modules.knowledge.models import (
    Artifact,
    Document,
    DocumentVersion,
    KnowledgeChunk,
)
from supportdesk.modules.messaging.models import ConversationEvent, Message
from supportdesk.modules.workspaces.models import Actor, RateLimitBucket, Workspace

create_app()


def main() -> None:
    deleted = 0
    with Session(worker_engine()) as db, db.begin():
        expired = db.scalars(
            select(Workspace.id).where(Workspace.expires_at <= now()).with_for_update()
        ).all()
        for workspace_id in expired:
            user_ids = list(
                db.scalars(
                    select(Actor.user_id).where(
                        Actor.workspace_id == workspace_id, Actor.user_id.is_not(None)
                    )
                )
            )
            for user_id in user_ids:
                other = db.scalar(
                    select(Actor.id)
                    .where(Actor.user_id == user_id, Actor.workspace_id != workspace_id)
                    .limit(1)
                )
                if other is None:
                    db.execute(
                        update(LoginSession)
                        .where(LoginSession.staff_user_id == user_id)
                        .values(revoked_at=now())
                    )
            actors = select(Actor.id).where(Actor.workspace_id == workspace_id)
            db.execute(
                update(LoginSession)
                .where(LoginSession.visitor_actor_id.in_(actors))
                .values(revoked_at=now())
            )
            db.execute(
                delete(LoginSession).where(LoginSession.visitor_actor_id.in_(actors))
            )
            db.execute(
                update(Document)
                .where(Document.workspace_id == workspace_id)
                .values(active_version_id=None)
            )
            for name in [
                "read_cursors",
                "message_citations",
                "run_sources",
                "ai_attempts",
                "usage_reservations",
                "messages",
                "ai_runs",
                "conversation_events",
                "command_receipts",
                "audit_log",
                "knowledge_chunks",
                "document_versions",
                "documents",
                "artifacts",
                "outbox",
                "jobs",
                "usage_periods",
                "conversations",
                "workspace_actors",
            ]:
                table = Base.metadata.tables[name]
                db.execute(delete(table).where(table.c.workspace_id == workspace_id))
            db.execute(delete(Workspace).where(Workspace.id == workspace_id))
            deleted += 1
        db.execute(delete(RateLimitBucket).where(RateLimitBucket.expires_at < now()))
        stamp = now()
        old_messages = select(Message.id).where(
            Message.created_at < stamp - timedelta(days=90)
        )
        db.execute(
            delete(MessageCitation).where(MessageCitation.message_id.in_(old_messages))
        )
        db.execute(
            delete(Message).where(Message.created_at < stamp - timedelta(days=90))
        )
        db.execute(
            delete(ConversationEvent).where(
                ConversationEvent.created_at < stamp - timedelta(days=30)
            )
        )
        db.execute(
            delete(Outbox).where(
                Outbox.status == "published",
                Outbox.published_at < stamp - timedelta(days=7),
            )
        )
        db.execute(
            delete(CommandReceipt).where(
                CommandReceipt.created_at < stamp - timedelta(days=30)
            )
        )
        db.execute(
            delete(AuditRecord).where(
                AuditRecord.created_at < stamp - timedelta(days=90)
            )
        )
        # AI job identity tombstones remain while a retained run references them.
        db.execute(
            delete(Job).where(
                Job.status.in_(["succeeded", "failed", "cancelled"]),
                Job.created_at < stamp - timedelta(days=30),
                ~Job.id.in_(select(AiRun.job_id)),
            )
        )
        withdrawn = (
            select(DocumentVersion.id)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(Document.withdrawn_at < stamp - timedelta(days=30))
        )
        db.execute(
            update(RunSource)
            .where(RunSource.version_id.in_(withdrawn))
            .values(chunk_id=None)
        )
        db.execute(
            update(MessageCitation)
            .where(MessageCitation.version_id.in_(withdrawn))
            .values(chunk_id=None)
        )
        db.execute(
            delete(KnowledgeChunk).where(KnowledgeChunk.version_id.in_(withdrawn))
        )
        purge_artifacts = select(DocumentVersion.artifact_id).where(
            DocumentVersion.id.in_(withdrawn)
        )
        active_artifacts = select(DocumentVersion.artifact_id).where(
            DocumentVersion.status.in_(["pending", "processing", "ready"])
        )
        db.execute(
            update(Artifact)
            .where(Artifact.id.in_(purge_artifacts), ~Artifact.id.in_(active_artifacts))
            .values(state="purged")
        )
        referenced = set(
            db.scalars(
                select(Artifact.storage_key).where(Artifact.state == "ready")
            ).all()
        )
    root = get_settings().storage_root
    removed = 0
    if root.exists():
        cutoff = (now() - timedelta(hours=24)).timestamp()
        for path in root.iterdir():
            if (
                path.is_file()
                and path.name not in referenced
                and path.stat().st_mtime < cutoff
            ):
                path.unlink()
                removed += 1
    print(f"Expired workspaces: {deleted}; old orphan files removed: {removed}")


if __name__ == "__main__":
    main()

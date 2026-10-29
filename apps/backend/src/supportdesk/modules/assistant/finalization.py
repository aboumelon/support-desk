import hashlib
import re
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from supportdesk.infrastructure.database import now
from supportdesk.modules.assistant.models import (
    AiAttempt,
    AiRun,
    MessageCitation,
    RunSource,
    UsagePeriod,
    UsageReservation,
)
from supportdesk.modules.conversations.models import Conversation
from supportdesk.modules.jobs.models import Job, Outbox
from supportdesk.modules.jobs.service import owns
from supportdesk.modules.knowledge.models import Document
from supportdesk.modules.messaging.models import ConversationEvent, Message
from supportdesk.modules.workspaces.models import Actor, Workspace


def emit(
    db: Session, conversation: Conversation, event_type: str, payload: dict[str, object]
) -> None:
    conversation.last_event_seq += 1
    conversation.updated_at = now()
    event_id = uuid4()
    db.add(
        ConversationEvent(
            id=event_id,
            workspace_id=conversation.workspace_id,
            conversation_id=conversation.id,
            seq=conversation.last_event_seq,
            type=event_type,
            payload=payload,
        )
    )
    db.add(
        Outbox(
            workspace_id=conversation.workspace_id,
            kind="conversation.notify",
            reference_id=conversation.id,
            dedupe_key=f"event:{event_id}",
        )
    )


def settle(db: Session, run: AiRun) -> None:
    period = db.scalar(
        select(UsagePeriod)
        .where(
            UsagePeriod.workspace_id == run.workspace_id,
            UsagePeriod.period == run.period,
        )
        .with_for_update()
    )
    reservation = db.scalar(
        select(UsageReservation)
        .where(UsageReservation.ai_run_id == run.id)
        .with_for_update()
    )
    if period is None or reservation is None:
        return
    attempts = db.scalars(select(AiAttempt).where(AiAttempt.run_id == run.id)).all()
    charged = sum(
        (a.input_tokens or 0) + (a.output_tokens or 0)
        if a.usage_state == "known"
        else run.per_attempt_tokens
        for a in attempts
    )
    period.charged_tokens -= reservation.charged_tokens - charged
    reservation.charged_tokens, reservation.state = charged, "settled"


def finish(
    db: Session,
    job_id: UUID,
    token: UUID,
    answer: str | None,
    reason: str | None = None,
) -> bool:
    info = db.get(Job, job_id)
    if info is None:
        return False
    run = db.get(AiRun, info.resource_id)
    if run is None:
        return False
    sources = db.scalars(
        select(RunSource)
        .where(RunSource.run_id == run.id)
        .order_by(RunSource.source_label)
    ).all()
    documents = {}
    for source in sorted(sources, key=lambda s: str(s.document_id)):
        if source.document_id not in documents:
            documents[source.document_id] = db.scalar(
                select(Document)
                .where(
                    Document.workspace_id == run.workspace_id,
                    Document.id == source.document_id,
                )
                .with_for_update()
            )
    conversation = db.scalar(
        select(Conversation)
        .where(
            Conversation.id == run.conversation_id,
            Conversation.workspace_id == run.workspace_id,
        )
        .with_for_update()
    )
    db.execute(
        select(UsagePeriod)
        .where(
            UsagePeriod.workspace_id == run.workspace_id,
            UsagePeriod.period == run.period,
        )
        .with_for_update()
    )
    run = db.scalar(
        select(AiRun)
        .where(AiRun.id == run.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    job = db.scalar(
        select(Job)
        .where(Job.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert run is not None and job is not None and conversation is not None
    workspace = db.get(Workspace, run.workspace_id)
    valid_lease = owns(job, token)
    valid_state = (
        conversation.status == "open"
        and conversation.controller == "bot"
        and conversation.control_epoch == run.expected_control_epoch
        and run.status in {"queued", "running"}
        and workspace is not None
        and (workspace.expires_at is None or workspace.expires_at > now())
    )
    if not valid_lease or not valid_state:
        if run.status in {"queued", "running"} and (valid_lease or not valid_state):
            run.status, run.finished_at = "superseded", now()
        if not valid_state and (job.lease_token == token or job.status == "cancelled"):
            job.status = "cancelled"
            settle(db, run)
        return False
    source_valid = True
    for source in sources:
        document = documents[source.document_id]
        if (
            document is None
            or document.withdrawn_at is not None
            or document.active_version_id != source.version_id
        ):
            source_valid = False
    labels = set(re.findall(r"\[(S\d+)\]", answer or ""))
    if not source_valid:
        reason = "KNOWLEDGE_CHANGED"
    if answer and (
        not labels
        or not labels.issubset({s.source_label for s in sources})
        or "NO_ANSWER" in answer
    ):
        reason = "INVALID_CITATION"
    if reason or not answer:
        conversation.controller, conversation.assigned_actor_id = "queue", None
        conversation.control_epoch += 1
        conversation.state_version += 1
        run.status, run.error_code = "failed", reason or "NO_EVIDENCE"
        emit(
            db,
            conversation,
            "conversation.control_changed",
            {
                "controller": "queue",
                "control_epoch": conversation.control_epoch,
                "state_version": conversation.state_version,
                "reason": run.error_code,
            },
        )
    else:
        assistant = db.scalar(
            select(Actor).where(
                Actor.workspace_id == run.workspace_id,
                Actor.kind == "assistant",
                Actor.active.is_(True),
            )
        )
        assert assistant is not None
        message = Message(
            id=uuid4(),
            workspace_id=run.workspace_id,
            conversation_id=conversation.id,
            sender_actor_id=assistant.id,
            sender_kind="assistant",
            body=answer,
            body_hash=hashlib.sha256(answer.encode()).hexdigest(),
            event_seq=conversation.last_event_seq + 1,
            ai_run_id=run.id,
            created_at=now(),
        )
        db.add(message)
        db.flush()
        for source in sources:
            if source.source_label in labels:
                db.add(
                    MessageCitation(
                        workspace_id=run.workspace_id,
                        message_id=message.id,
                        source_label=source.source_label,
                        version_id=source.version_id,
                        chunk_id=source.chunk_id,
                        document_id=source.document_id,
                        title=source.title,
                        excerpt=source.excerpt,
                        locator=source.locator,
                    )
                )
        run.status, run.output_message_id = "succeeded", message.id
        emit(
            db,
            conversation,
            "message.created",
            {
                "id": str(message.id),
                "sender_kind": "assistant",
                "body": answer,
                "ai_run_id": str(run.id),
            },
        )
    run.finished_at, job.status, job.leased_until = (
        now(),
        "succeeded" if run.status == "succeeded" else "failed",
        None,
    )
    emit(
        db,
        conversation,
        "ai.run_changed",
        {"run_id": str(run.id), "status": run.status},
    )
    settle(db, run)
    return run.status == "succeeded"


def recover_terminal_run(db: Session, run_id: UUID) -> None:
    info = db.get(AiRun, run_id)
    if info is None:
        return
    conversation = db.scalar(
        select(Conversation)
        .where(Conversation.id == info.conversation_id)
        .with_for_update()
    )
    db.execute(
        select(UsagePeriod)
        .where(
            UsagePeriod.workspace_id == info.workspace_id,
            UsagePeriod.period == info.period,
        )
        .with_for_update()
    )
    run = db.scalar(
        select(AiRun)
        .where(AiRun.id == run_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    assert run is not None
    job = db.scalar(select(Job).where(Job.id == run.job_id).with_for_update())
    if (
        job is None
        or job.status not in {"failed", "cancelled"}
        or run.status not in {"queued", "running"}
    ):
        return
    if (
        conversation
        and conversation.status == "open"
        and conversation.controller == "bot"
        and conversation.control_epoch == run.expected_control_epoch
    ):
        conversation.controller = "queue"
        conversation.control_epoch += 1
        conversation.state_version += 1
        emit(
            db,
            conversation,
            "conversation.control_changed",
            {
                "controller": "queue",
                "control_epoch": conversation.control_epoch,
                "state_version": conversation.state_version,
                "reason": "ATTEMPTS_EXHAUSTED",
            },
        )
    run.status, run.error_code, run.finished_at = (
        "failed",
        job.error_code or "JOB_CANCELLED",
        now(),
    )
    settle(db, run)

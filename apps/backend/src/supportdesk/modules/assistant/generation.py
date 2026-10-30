import json
import time
from datetime import timedelta
from uuid import UUID

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from supportdesk.config import get_settings
from supportdesk.infrastructure.database import now
from supportdesk.infrastructure.logging import job_event
from supportdesk.infrastructure.worker_database import worker_engine
from supportdesk.modules.assistant.embeddings.e5 import encode
from supportdesk.modules.assistant.finalization import emit, finish
from supportdesk.modules.assistant.models import AiAttempt, AiRun, RunSource
from supportdesk.modules.assistant.prompts import REFERENCE_MARKER, build_messages
from supportdesk.modules.assistant.providers.base import ProviderFailure
from supportdesk.modules.assistant.providers.compatible_http import (
    CompatibleHttpProvider,
)
from supportdesk.modules.assistant.providers.fake import FakeProvider
from supportdesk.modules.conversations.models import Conversation
from supportdesk.modules.jobs.models import Job
from supportdesk.modules.jobs.service import owns
from supportdesk.modules.knowledge.retrieval import Passage, retrieve
from supportdesk.modules.messaging.models import Message
from supportdesk.modules.workspaces.models import Workspace


def generate(job_id: UUID, token: UUID) -> None:
    with Session(worker_engine()) as db:
        job = db.get(Job, job_id)
        if job is None or not owns(job, token):
            return
        run = db.get(AiRun, job.resource_id)
        assert run is not None
        run_id, workspace, cid, epoch = (
            run.id,
            run.workspace_id,
            run.conversation_id,
            run.expected_control_epoch,
        )
        trigger = db.scalar(
            select(Message).where(
                Message.workspace_id == workspace,
                Message.conversation_id == cid,
                Message.event_seq == run.trigger_message_seq,
            )
        )
        assert trigger is not None
        configured = (
            "fixture-v1"
            if get_settings().llm_provider == "fake"
            else get_settings().llm_model
        )
        if run.provider_model != configured:
            raise ProviderFailure("PROVIDER_CONFIGURATION_CHANGED")
        if run.prompt_version != "answer-v2":
            raise ProviderFailure("PROMPT_CONFIGURATION_CHANGED")
        query = trigger.body
    vector = encode([query], "query")[0]
    with Session(worker_engine()) as db:
        passages = retrieve(db, workspace, vector)
        selected: list[Passage] = []
        remaining = 2000
        for passage in passages:
            if len(selected) == 4:
                break
            if passage.chunk.token_count <= remaining:
                selected.append(passage)
                remaining -= passage.chunk.token_count
        if not selected or selected[0].score < 0.65:
            with db.begin_nested():
                finish(db, job_id, token, None, "NO_EVIDENCE")
            db.commit()
            return
        source_values = [
            {
                "workspace_id": workspace,
                "run_id": run_id,
                "source_label": f"S{i + 1}",
                "chunk_id": p.chunk.id,
                "version_id": p.chunk.version_id,
                "document_id": p.document_id,
                "title": p.title,
                "excerpt": p.chunk.text,
                "locator": f"page {p.chunk.page_start}; {p.chunk.heading_path}",
            }
            for i, p in enumerate(selected)
        ]
        history = db.scalars(
            select(Message)
            .where(
                Message.workspace_id == workspace,
                Message.conversation_id == cid,
                Message.event_seq <= run.trigger_message_seq,
            )
            .order_by(Message.event_seq.desc())
            .limit(30)
        ).all()
        turns = [
            ("assistant" if m.sender_kind in {"assistant", "staff"} else "user", m.body)
            for m in reversed(history)
        ]
    with Session(worker_engine()) as db, db.begin():
        conversation = db.scalar(
            select(Conversation).where(Conversation.id == cid).with_for_update()
        )
        run = db.scalar(select(AiRun).where(AiRun.id == run_id).with_for_update())
        job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
        assert conversation is not None and run is not None and job is not None
        active_workspace = db.get(Workspace, workspace)
        if active_workspace is None or (
            active_workspace.expires_at and active_workspace.expires_at <= now()
        ):
            return
        if (
            not owns(job, token)
            or run.status not in {"queued", "running"}
            or conversation.control_epoch != epoch
            or conversation.controller != "bot"
        ):
            return
        sources = db.scalars(
            select(RunSource)
            .where(RunSource.run_id == run_id)
            .order_by(RunSource.source_label)
        ).all()
        if not sources:
            sources = [RunSource(**values) for values in source_values]

        run.status = "running"
        attempt = job.attempt
        per_attempt = run.per_attempt_tokens
        messages = build_messages(
            [
                {"label": source.source_label, "text": source.excerpt}
                for source in sources
            ],
            turns,
            min(
                get_settings().input_allowance(),
                per_attempt - get_settings().ai_max_output_tokens,
            ),
        )
        included = {
            source["label"]
            for source in json.loads(
                messages[0]["content"].split(REFERENCE_MARKER, 1)[1]
            )["sources"]
        }
        for source in sources:
            if source.source_label not in included:
                if source in db:
                    db.expunge(source)
            elif source not in db:
                db.add(source)
        db.add(
            AiAttempt(
                workspace_id=workspace,
                run_id=run_id,
                attempt=attempt,
                usage_state="unknown",
            )
        )
        emit(
            db,
            conversation,
            "ai.run_changed",
            {"run_id": str(run_id), "status": "running", "control_epoch": epoch},
        )
    settings = get_settings()
    provider = (
        FakeProvider() if settings.llm_provider == "fake" else CompatibleHttpProvider()
    )
    answer = ""
    input_tokens = output_tokens = None
    started = time.monotonic()
    first_token = True
    chunk_index = 0
    redis = Redis.from_url(
        settings.redis_url, socket_connect_timeout=1, socket_timeout=1
    )
    try:
        for delta in provider.stream(messages, per_attempt):
            if time.monotonic() - started > settings.ai_total_timeout_seconds:
                raise ProviderFailure("PROVIDER_TIMEOUT", True)
            if delta.input_tokens is not None:
                input_tokens, output_tokens = delta.input_tokens, delta.output_tokens
            if delta.text:
                if first_token:
                    job_event(
                        "ai.first_token",
                        job_id=str(job_id),
                        run_id=str(run_id),
                        attempt=attempt,
                        seconds=time.monotonic() - started,
                    )
                    first_token = False
                # Check lease and epoch before each provisional publication.
                with Session(worker_engine()) as db:
                    current_job = db.get(Job, job_id)
                    current = db.get(Conversation, cid)
                    if (
                        current_job is None
                        or not owns(current_job, token)
                        or current is None
                        or current.control_epoch != epoch
                    ):
                        break
                answer += delta.text
                if len(answer.encode()) > 32768 or len(answer) > 8000:
                    raise ProviderFailure("OUTPUT_TOO_LARGE")
                try:
                    redis.publish(
                        f"sd:draft:{workspace}",
                        json.dumps(
                            {
                                "protocol_version": 1,
                                "type": "ai.delta",
                                "conversation_id": str(cid),
                                "run_id": str(run_id),
                                "control_epoch": epoch,
                                "attempt": attempt,
                                "chunk_index": chunk_index,
                                "text": delta.text,
                            }
                        ),
                    )
                except Exception:
                    pass
                chunk_index += 1
        with Session(worker_engine()) as db, db.begin():
            usage = db.scalar(
                select(AiAttempt).where(
                    AiAttempt.run_id == run_id, AiAttempt.attempt == attempt
                )
            )
            if usage:
                usage.input_tokens, usage.output_tokens = input_tokens, output_tokens
                usage.usage_state = (
                    "known"
                    if input_tokens is not None and output_tokens is not None
                    else "unknown"
                )
                usage.finished_at = now()
        with Session(worker_engine()) as db, db.begin():
            finish(db, job_id, token, answer)
    except ProviderFailure as exc:
        with Session(worker_engine()) as usage_db, usage_db.begin():
            usage = usage_db.scalar(
                select(AiAttempt).where(
                    AiAttempt.run_id == run_id, AiAttempt.attempt == attempt
                )
            )
            if usage:
                usage.input_tokens, usage.output_tokens = input_tokens, output_tokens
                usage.usage_state = (
                    "known"
                    if input_tokens is not None and output_tokens is not None
                    else "unknown"
                )
                usage.finished_at = now()
        with Session(worker_engine()) as db, db.begin():
            conversation = db.scalar(
                select(Conversation).where(Conversation.id == cid).with_for_update()
            )
            run = db.scalar(select(AiRun).where(AiRun.id == run_id).with_for_update())
            job = db.scalar(select(Job).where(Job.id == job_id).with_for_update())
            if job is None or not owns(job, token) or run is None:
                return
            if (
                exc.retryable
                and job.attempt < 3
                and conversation
                and conversation.control_epoch == epoch
                and run.status == "running"
            ):
                job.status, job.error_code, job.leased_until = "retry", exc.code, None
                job.available_at = now() + timedelta(
                    seconds=max(5 if job.attempt == 1 else 20, exc.retry_after or 0)
                )
                job.last_dispatched_at = None
                run.status = "queued"
                emit(
                    db,
                    conversation,
                    "ai.run_changed",
                    {"run_id": str(run_id), "status": "queued"},
                )
            else:
                # Reacquire locks in source/conversation order.
                db.rollback()
                with Session(worker_engine()) as terminal_db, terminal_db.begin():
                    finish(terminal_db, job_id, token, None, exc.code)
    finally:
        redis.close()

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from supportdesk.api.errors import Problem
from supportdesk.modules.audit.models import AuditRecord
from supportdesk.modules.conversations.schemas import ControlInput, ConversationView
from supportdesk.modules.conversations.service import (
    emit,
    load_conversation,
    receipt,
    save_receipt,
)
from supportdesk.modules.workspaces.models import Actor


async def control(
    db: AsyncSession,
    actor: Actor,
    conversation_id: UUID,
    action: str,
    body: ControlInput,
    key: str,
) -> ConversationView:
    conversation = await load_conversation(db, actor, conversation_id)
    if actor.kind == "visitor" and action not in {"handoff", "reopen"}:
        raise Problem(403, "FORBIDDEN")
    operation = f"{action}:{conversation_id}"
    payload = body.model_dump(mode="json")
    prior = await receipt(db, actor, operation, key, payload)
    if prior:
        return ConversationView.model_validate(prior)
    if (
        action == "handoff"
        and conversation.controller in {"queue", "human"}
        and conversation.status == "open"
    ):
        result = ConversationView.model_validate(conversation)
        save_receipt(db, actor, operation, key, payload, result.model_dump(mode="json"))
        return result
    if body.expected_state_version != conversation.state_version:
        raise Problem(
            409,
            "CONVERSATION_VERSION_CONFLICT",
            current_state_version=conversation.state_version,
        )
    if action == "reopen":
        if conversation.status != "resolved":
            raise Problem(409, "INVALID_TRANSITION")
        conversation.status = "open"
        conversation.controller = "queue"
        conversation.assigned_actor_id = None
    else:
        if conversation.status != "open":
            raise Problem(409, "INVALID_TRANSITION")
        if action == "claim":
            if conversation.controller != "queue":
                raise Problem(409, "INVALID_TRANSITION")
            conversation.controller = "human"
            conversation.assigned_actor_id = actor.id
        elif action == "reassign":
            if actor.role != "admin" or body.assigned_actor_id is None:
                raise Problem(403, "FORBIDDEN")
            target = await db.scalar(
                select(Actor).where(
                    Actor.workspace_id == actor.workspace_id,
                    Actor.id == body.assigned_actor_id,
                    Actor.kind == "staff",
                    Actor.active.is_(True),
                )
            )
            if not target:
                raise Problem(404, "RESOURCE_NOT_FOUND")
            conversation.controller = "human"
            conversation.assigned_actor_id = target.id
        elif action in {"release", "resolve", "return-to-bot"}:
            if actor.role != "admin" and conversation.assigned_actor_id != actor.id:
                raise Problem(409, "NOT_ASSIGNED")
            if action == "return-to-bot":
                if conversation.controller != "human":
                    raise Problem(409, "INVALID_TRANSITION")
                from supportdesk.modules.assistant.service import ready

                if not await ready(db, actor.workspace_id):
                    raise Problem(409, "ASSISTANT_UNAVAILABLE")
                conversation.controller = "bot"
                conversation.assigned_actor_id = None
            elif action == "release":
                if conversation.controller != "human":
                    raise Problem(409, "INVALID_TRANSITION")
                conversation.controller = "queue"
                conversation.assigned_actor_id = None
            else:
                conversation.status = "resolved"
        elif action == "handoff":
            conversation.controller = "queue"
            conversation.assigned_actor_id = None
        else:
            raise Problem(404, "RESOURCE_NOT_FOUND")
    from supportdesk.modules.assistant.service import supersede

    await supersede(db, conversation)
    conversation.state_version += 1
    conversation.control_epoch += 1
    kind = {"resolve": "conversation.resolved", "reopen": "conversation.reopened"}.get(
        action, "conversation.control_changed"
    )
    await emit(
        db,
        conversation,
        kind,
        {
            "action": action,
            "actor_id": str(actor.id),
            "actor_kind": actor.kind,
            "controller": conversation.controller,
            "status": conversation.status,
            "assigned_actor_id": str(conversation.assigned_actor_id)
            if conversation.assigned_actor_id
            else None,
            "state_version": conversation.state_version,
            "control_epoch": conversation.control_epoch,
        },
    )
    if actor.kind == "staff":
        db.add(
            AuditRecord(
                workspace_id=actor.workspace_id,
                actor_id=actor.id,
                action=action,
                subject_id=conversation.id,
            )
        )
    result = ConversationView.model_validate(conversation)
    save_receipt(db, actor, operation, key, payload, result.model_dump(mode="json"))
    return result

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, RootModel


class DurableEvent(BaseModel):
    protocol_version: Literal[1] = 1
    type: Literal[
        "conversation.created",
        "message.created",
        "conversation.control_changed",
        "conversation.resolved",
        "conversation.reopened",
        "read_cursor.updated",
        "ai.run_changed",
    ]
    event_id: UUID
    conversation_id: UUID
    seq: int = Field(ge=1)
    occurred_at: datetime
    data: dict[str, str | int | bool | None]


class Subscribe(BaseModel):
    protocol_version: Literal[1] = 1
    type: Literal["subscribe"]
    conversation_id: UUID
    after_seq: int = Field(ge=0)


class AiDelta(BaseModel):
    protocol_version: Literal[1] = 1
    type: Literal["ai.delta"]
    conversation_id: UUID
    run_id: UUID
    control_epoch: int = Field(ge=0)
    attempt: int = Field(ge=1, le=3)
    chunk_index: int = Field(ge=0)
    text: str = Field(max_length=8000)


class TypingUpdate(BaseModel):
    protocol_version: Literal[1] = 1
    type: Literal["typing.updated"]
    conversation_id: UUID
    actor_id: UUID
    expires_in: Literal[5] = 5


class PresenceUpdate(BaseModel):
    protocol_version: Literal[1] = 1
    type: Literal["presence.updated"]
    conversation_id: UUID
    actor_id: UUID
    online: bool


class RealtimeFrame(RootModel[DurableEvent | AiDelta | TypingUpdate | PresenceUpdate]):
    pass

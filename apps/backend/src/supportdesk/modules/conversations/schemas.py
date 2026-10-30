from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from supportdesk.modules.assistant.schemas import RunView


class ConversationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    workspace_id: UUID
    visitor_actor_id: UUID
    status: Literal["open", "resolved"]
    controller: Literal["bot", "queue", "human"]
    assigned_actor_id: UUID | None
    state_version: int
    control_epoch: int
    last_event_seq: int
    updated_at: datetime
    unread_count: int = 0
    title: str | None = None
    last_message_preview: str | None = None
    last_message_kind: str | None = None


class MessageInput(BaseModel):
    client_message_id: UUID
    body: str = Field(min_length=1, max_length=8000)

    @field_validator("body")
    @classmethod
    def validate_body(cls, value: str) -> str:
        if not value.strip() or len(value.encode("utf-8")) > 32768:
            raise ValueError("Message must contain text and fit in 32 KiB")
        return value


class MessageView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    conversation_id: UUID
    sender_actor_id: UUID
    sender_kind: str
    client_message_id: UUID | None
    body: str
    event_seq: int
    created_at: datetime


class SendResult(BaseModel):
    message: MessageView
    conversation: ConversationView


class Snapshot(BaseModel):
    conversation: ConversationView
    messages: list[MessageView]
    event_cursor: int
    active_run: RunView | None = None
    read_cursors: dict[str, int]


class ControlInput(BaseModel):
    expected_state_version: int = Field(ge=1)
    assigned_actor_id: UUID | None = None


class ReadInput(BaseModel):
    last_read_seq: int = Field(ge=1)

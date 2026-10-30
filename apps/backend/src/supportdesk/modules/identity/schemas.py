from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class LoginInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=1024)


class Membership(BaseModel):
    workspace_id: UUID
    actor_id: UUID
    name: str
    role: str
    fictional_data: bool = False


class SessionView(BaseModel):
    audience: Literal["staff", "visitor"]
    csrf_token: str
    expires_at: datetime
    actor_id: UUID | None = None
    workspace_id: UUID | None = None
    public_key: str | None = None
    memberships: list[Membership] = []
    provider_mode: str
    fictional_data: bool = False
    ai_available: bool = True


class PublicCapabilities(BaseModel):
    demo_available: bool
    ai_mode: Literal["simulated", "live", "disabled"]


class WorkspaceView(BaseModel):
    id: UUID
    name: str
    public_key: str
    role: str | None
    ai_enabled: bool

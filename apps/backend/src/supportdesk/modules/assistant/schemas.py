from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RunView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    status: str
    expected_control_epoch: int
    error_code: str | None
    provider_model: str


class CitationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source_label: str
    title: str
    excerpt: str
    locator: str
    available: bool = True


class AssistantSetting(BaseModel):
    enabled: bool

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class VersionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    version_no: int
    status: str
    error_code: str | None
    embedding_revision: str


class DocumentView(BaseModel):
    id: UUID
    title: str
    active_version_id: UUID | None
    withdrawn_at: datetime | None
    versions: list[VersionView]


class UploadResult(BaseModel):
    document_id: UUID
    version_id: UUID
    job_id: UUID


class JobView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    kind: str
    status: str
    attempt: int
    error_code: str | None

from dataclasses import dataclass
from typing import cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from supportdesk.modules.knowledge.models import (
    Document,
    DocumentVersion,
    KnowledgeChunk,
)


@dataclass
class Passage:
    chunk: KnowledgeChunk
    document_id: UUID
    title: str
    score: float


def retrieve(
    db: Session, workspace_id: UUID, vector: list[float], limit: int = 8
) -> list[Passage]:
    distance = KnowledgeChunk.embedding.cosine_distance(vector)
    rows = db.execute(
        select(KnowledgeChunk, Document.id, Document.title, distance)
        .join(
            DocumentVersion,
            (DocumentVersion.id == KnowledgeChunk.version_id)
            & (DocumentVersion.workspace_id == KnowledgeChunk.workspace_id),
        )
        .join(
            Document,
            (Document.id == DocumentVersion.document_id)
            & (Document.workspace_id == KnowledgeChunk.workspace_id),
        )
        .where(
            KnowledgeChunk.workspace_id == workspace_id,
            Document.withdrawn_at.is_(None),
            Document.active_version_id == DocumentVersion.id,
            DocumentVersion.status == "ready",
        )
        .order_by(distance)
        .limit(min(limit, 8))
    ).all()
    result = []
    for row in rows:
        chunk, document_id, title, score = cast(
            tuple[KnowledgeChunk, UUID, str, float], tuple(row)
        )
        result.append(Passage(chunk, document_id, title, 1 - float(score)))
    return result

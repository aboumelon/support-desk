import re
from functools import lru_cache
from typing import Any

from supportdesk.config import get_settings


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.translate(str.maketrans("يك\u200c", "یک "))).strip()


@lru_cache
def model() -> Any:
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    return SentenceTransformer(
        settings.embedding_model,
        revision=settings.embedding_revision,
        cache_folder=str(settings.model_cache),
        device="cpu",
        local_files_only=True,
    )


def encode(texts: list[str], purpose: str = "passage") -> list[list[float]]:
    embeddings = model().encode(
        [f"{purpose}: {normalize(text)}" for text in texts],
        normalize_embeddings=True,
        batch_size=16,
        show_progress_bar=False,
    )
    return embeddings.tolist()  # type: ignore[no-any-return]

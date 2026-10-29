"""Explicit model preparation; API/worker requests never download weights."""

from huggingface_hub import snapshot_download

from supportdesk.config import get_settings

if __name__ == "__main__":
    settings = get_settings()
    snapshot_download(
        settings.embedding_model,
        revision=settings.embedding_revision,
        cache_dir=str(settings.model_cache),
        allow_patterns=[
            "*.json",
            "*.safetensors",
            "tokenizer*",
            "sentencepiece*",
            "*.model",
            "modules.json",
        ],
    )
    print(f"Provisioned {settings.embedding_model}@{settings.embedding_revision}")

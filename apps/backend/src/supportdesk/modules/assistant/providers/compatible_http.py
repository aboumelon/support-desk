import json
import time
from collections.abc import Iterator

import httpx

from supportdesk.config import get_settings
from supportdesk.modules.assistant.providers.base import Delta, ProviderFailure


class CompatibleHttpProvider:
    def stream(
        self, messages: list[dict[str, str]], context_limit: int
    ) -> Iterator[Delta]:
        settings = get_settings()
        if (
            sum(len(m["content"].encode()) for m in messages)
            + settings.ai_max_output_tokens
            > context_limit
        ):
            raise ProviderFailure("PROMPT_TOO_LARGE")
        if not settings.llm_base_url:
            raise ProviderFailure("INVALID_PROVIDER_CONFIGURATION")
        started = time.monotonic()
        try:
            with httpx.Client(
                timeout=httpx.Timeout(15, connect=5), trust_env=False
            ) as client:
                with client.stream(
                    "POST",
                    f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "messages": messages,
                        "stream": True,
                        "stream_options": {"include_usage": True},
                        "max_tokens": settings.ai_max_output_tokens,
                    },
                ) as response:
                    if response.status_code != 200:
                        raise ProviderFailure(
                            "PROVIDER_RATE_LIMITED"
                            if response.status_code == 429
                            else "PROVIDER_HTTP_ERROR",
                            response.status_code == 429 or response.status_code >= 500,
                        )
                    completed = False
                    for line in response.iter_lines():
                        if (
                            time.monotonic() - started
                            > settings.ai_total_timeout_seconds
                        ):
                            raise ProviderFailure("PROVIDER_TIMEOUT", True)
                        if len(line) > 65536:
                            raise ProviderFailure("INVALID_PROVIDER_FRAME")
                        if not line.startswith("data:"):
                            continue
                        content = line[5:].strip()
                        if content == "[DONE]":
                            completed = True
                            break
                        frame = json.loads(content)
                        usage = frame.get("usage") or {}
                        if usage:
                            yield Delta(
                                input_tokens=usage.get("prompt_tokens"),
                                output_tokens=usage.get("completion_tokens"),
                            )
                        for choice in frame.get("choices", []):
                            text = choice.get("delta", {}).get("content")
                            if text:
                                yield Delta(text=text)
                    if not completed:
                        raise ProviderFailure("PROVIDER_STREAM_DROPPED", True)
        except httpx.TimeoutException as exc:
            raise ProviderFailure("PROVIDER_TIMEOUT", True) from exc
        except httpx.TransportError as exc:
            raise ProviderFailure("PROVIDER_UNAVAILABLE", True) from exc

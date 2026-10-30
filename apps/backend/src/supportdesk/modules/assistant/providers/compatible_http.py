"""Bounded OpenAI-compatible SSE adapter. No endpoint errors include response bodies."""

import asyncio
import json
import math
import time
from collections.abc import AsyncGenerator, AsyncIterator, Iterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import cast

import httpx

from supportdesk.config import get_settings
from supportdesk.modules.assistant.prompts import input_size
from supportdesk.modules.assistant.providers.base import Delta, ProviderFailure


def retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            stamp = parsedate_to_datetime(value)
            seconds = (stamp - datetime.now(UTC)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            return None
    return max(0.0, seconds) if math.isfinite(seconds) else None


async def sse_data(response: httpx.Response) -> AsyncIterator[str]:
    buffer = b""
    event: list[str] = []
    event_size = total = 0
    async for chunk in response.aiter_bytes():
        total += len(chunk)
        if total > 1048576:
            raise ProviderFailure("INVALID_PROVIDER_FRAME")
        buffer += chunk
        while b"\n" in buffer:
            raw, buffer = buffer.split(b"\n", 1)
            if len(raw) > 65536:
                raise ProviderFailure("INVALID_PROVIDER_FRAME")
            line = raw.rstrip(b"\r").decode("utf-8")
            if not line:
                if event:
                    yield "\n".join(event)
                    event, event_size = [], 0
            elif line.startswith("data:"):
                value = line[5:].lstrip(" ")
                event.append(value)
                event_size += len(raw)
                if event_size > 65536:
                    raise ProviderFailure("INVALID_PROVIDER_FRAME")
        if len(buffer) > 65536:
            raise ProviderFailure("INVALID_PROVIDER_FRAME")
    # A truncated event or missing DONE is not a completed answer.
    if buffer or event:
        raise ProviderFailure("PROVIDER_STREAM_DROPPED", True)


class CompatibleHttpProvider:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout_seconds: float | None = None,
    ):
        self.transport, self.timeout_seconds = transport, timeout_seconds

    def stream(
        self, messages: list[dict[str, str]], context_limit: int
    ) -> Iterator[Delta]:
        settings = get_settings()
        if input_size(messages) > min(
            settings.input_allowance(), context_limit - settings.ai_max_output_tokens
        ):
            raise ProviderFailure("PROMPT_TOO_LARGE")
        if not settings.llm_base_url:
            raise ProviderFailure("INVALID_PROVIDER_CONFIGURATION")
        if (
            not messages
            or messages[0]["role"] != "system"
            or any(m["role"] == "system" for m in messages[1:])
        ):
            raise ProviderFailure("INVALID_PROMPT")
        deadline = time.monotonic() + min(
            self.timeout_seconds or settings.ai_total_timeout_seconds,
            settings.ai_total_timeout_seconds,
        )
        # Running each next() under its remaining deadline makes a stalled connection
        # cancellable without a provider thread or holding any database transaction.
        stream = self._stream(messages)
        with asyncio.Runner() as runner:
            try:
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise ProviderFailure("PROVIDER_TIMEOUT", True)
                    try:
                        delta = runner.run(asyncio.wait_for(anext(stream), remaining))
                    except StopAsyncIteration:
                        return
                    yield delta
            except (TimeoutError, httpx.TimeoutException) as exc:
                raise ProviderFailure("PROVIDER_TIMEOUT", True) from exc
            except httpx.TransportError as exc:
                raise ProviderFailure("PROVIDER_UNAVAILABLE", True) from exc
            except (ValueError, KeyError, TypeError, UnicodeError) as exc:
                raise ProviderFailure("INVALID_PROVIDER_FRAME") from exc
            finally:
                runner.run(stream.aclose())

    async def _stream(self, messages: list[dict[str, str]]) -> AsyncGenerator[Delta]:
        settings = get_settings()
        timeout = httpx.Timeout(
            settings.llm_read_timeout_seconds,
            connect=settings.llm_connect_timeout_seconds,
        )
        async with httpx.AsyncClient(
            timeout=timeout,
            trust_env=False,
            transport=self.transport,
            follow_redirects=False,
        ) as client:
            async with client.stream(
                "POST",
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",  # type: ignore[union-attr]
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
                    wait = retry_after(response.headers.get("Retry-After"))
                    transient = (
                        response.status_code == 429 or response.status_code >= 500
                    )
                    # Never shorten a server-specified wait. Long waits end this run.
                    if wait is not None and wait > settings.llm_retry_after_max_seconds:
                        transient = False
                    raise ProviderFailure(
                        "PROVIDER_RATE_LIMITED"
                        if response.status_code == 429
                        else "PROVIDER_HTTP_ERROR",
                        transient,
                        wait,
                    )
                if (
                    "text/event-stream"
                    not in response.headers.get("content-type", "").lower()
                ):
                    raise ProviderFailure("INVALID_PROVIDER_FRAME")
                stopped = False
                terminal_error: str | None = None
                final_usage: tuple[int, int] | None = None
                frames = 0
                async for content in sse_data(response):
                    frames += 1
                    if frames > 4096:
                        raise ProviderFailure("INVALID_PROVIDER_FRAME")
                    if content.strip() == "[DONE]":
                        if not stopped:
                            raise ProviderFailure("PROVIDER_STREAM_DROPPED", True)
                        if final_usage:
                            yield Delta(
                                input_tokens=final_usage[0],
                                output_tokens=final_usage[1],
                            )
                        if terminal_error:
                            raise ProviderFailure(terminal_error)
                        return
                    frame = json.loads(content)
                    if not isinstance(frame, dict) or frame.get("error"):
                        raise ProviderFailure("INVALID_PROVIDER_FRAME")
                    choices = frame.get("choices", [])
                    if not isinstance(choices, list) or len(choices) > 1:
                        raise ProviderFailure("INVALID_PROVIDER_FRAME")
                    usage = frame.get("usage")
                    if usage is not None:
                        if not isinstance(usage, dict):
                            raise ProviderFailure("INVALID_PROVIDER_FRAME")
                        values = [
                            usage.get("prompt_tokens"),
                            usage.get("completion_tokens"),
                        ]
                        if all(value is None for value in values):
                            pass
                        elif not all(
                            type(value) is int and 0 <= value <= 10000000
                            for value in values
                        ):
                            raise ProviderFailure("INVALID_PROVIDER_FRAME")
                        else:
                            # Only completed usage releases reserved capacity. Early
                            # cumulative counters or a dropped stream stay unknown.
                            if stopped or any(
                                isinstance(choice, dict)
                                and choice.get("finish_reason") in {"stop", "length"}
                                for choice in choices
                            ):
                                final_usage = (
                                    cast(int, values[0]),
                                    cast(int, values[1]),
                                )
                    for choice in choices:
                        if not isinstance(choice, dict) or choice.get("index", 0) != 0:
                            raise ProviderFailure("INVALID_PROVIDER_FRAME")
                        reason = choice.get("finish_reason")
                        if reason is not None:
                            if reason == "length":
                                terminal_error = "PROVIDER_OUTPUT_TRUNCATED"
                            elif reason != "stop":
                                raise ProviderFailure("UNSUPPORTED_PROVIDER_OUTPUT")
                            stopped = True
                        delta = choice.get("delta", {})
                        if not isinstance(delta, dict) or delta.get("tool_calls"):
                            raise ProviderFailure("UNSUPPORTED_PROVIDER_OUTPUT")
                        value = delta.get("content")
                        if value is not None and not isinstance(value, str):
                            raise ProviderFailure("INVALID_PROVIDER_FRAME")
                        if value:
                            yield Delta(text=value)
                if terminal_error:
                    raise ProviderFailure(terminal_error)
                raise ProviderFailure("PROVIDER_STREAM_DROPPED", True)

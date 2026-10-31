"""Browser-test IPC barrier; never imported by production entrypoints."""

import re
import threading
import time
from collections.abc import Iterator
from pathlib import Path

MARKER = re.compile(r"\[e2e-cancel:([0-9a-f]{32})\]")


def require_test_worker(environment: str, provider: str, directory: Path) -> None:
    if environment != "test" or provider != "fake" or not directory.is_dir():
        raise RuntimeError(
            "E2E barrier requires APP_ENV=test, fake provider and IPC directory"
        )


def controlled_stream(
    stream: Iterator[object], directory: Path, token: str, timeout: float = 45
) -> Iterator[object]:
    def wait_for(signal: str) -> None:
        deadline = time.monotonic() + timeout
        while not (directory / f"{token}.{signal}").exists():
            if time.monotonic() >= deadline:
                (directory / f"{token}.timed-out").touch()
                raise TimeoutError("E2E cancellation barrier was not released")
            threading.Event().wait(0.01)  # Bounded IPC polling, not provider latency.

    # Prime the client snapshot/subscription before emitting the first ephemeral delta.
    (directory / f"{token}.ready").touch()
    wait_for("start")
    # The caller consumes/publishes this first delta before requesting the next one.
    yield next(stream)
    (directory / f"{token}.paused").touch()
    wait_for("release")
    yield from stream


def install(directory: Path) -> None:
    from supportdesk.config import get_settings
    from supportdesk.modules.assistant import generation
    from supportdesk.modules.assistant.providers.fake import FakeProvider

    settings = get_settings()
    require_test_worker(settings.app_env, settings.llm_provider, directory)
    original_stream = FakeProvider.stream
    original_generate = generation.generate
    active = threading.local()

    def stream(self, messages, context_limit):
        original = original_stream(self, messages, context_limit)
        question = next(m["content"] for m in reversed(messages) if m["role"] == "user")
        marker = MARKER.search(question)
        if marker and (directory / f"{marker[1]}.arm").exists():
            active.token = marker[1]
            yield from controlled_stream(original, directory, marker[1])
        else:
            yield from original

    def generate(job_id, lease_token):
        active.token = None
        try:
            return original_generate(job_id, lease_token)
        finally:
            if active.token:
                # Written only after the real generation/finalization transaction exits.
                (directory / f"{active.token}.finished").touch()

    FakeProvider.stream = stream
    generation.generate = generate

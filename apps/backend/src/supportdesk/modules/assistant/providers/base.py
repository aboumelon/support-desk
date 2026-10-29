from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol


class ProviderFailure(Exception):
    def __init__(self, code: str, retryable: bool = False):
        self.code, self.retryable = code, retryable
        super().__init__(code)


@dataclass
class Delta:
    text: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None


class ChatProvider(Protocol):
    def stream(
        self, messages: list[dict[str, str]], context_limit: int
    ) -> Iterator[Delta]: ...

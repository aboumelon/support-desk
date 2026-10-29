from dataclasses import dataclass
from typing import Any

from supportdesk.modules.knowledge.parsers import InvalidDocument


@dataclass
class Chunk:
    text: str
    page: int
    heading: str
    token_count: int


def chunks(pages: list[tuple[int, str]], tokenizer: Any) -> list[Chunk]:
    output = []
    total = 0
    heading = ""
    for page, text in pages:
        offsets = tokenizer(
            text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            truncation=False,
        )["offset_mapping"]
        total += len(offsets)
        if total > 50000:
            raise InvalidDocument("TOO_MANY_TOKENS")
        for start in range(0, len(offsets), 300):
            window = offsets[start : start + 350]
            if not window:
                continue
            passage = text[window[0][0] : window[-1][1]]
            headings = [
                line.strip("# ")
                for line in passage.splitlines()
                if line.startswith("#")
            ]
            if headings:
                heading = headings[-1][:300]
            output.append(Chunk(passage, page, heading, len(window)))
    if not output:
        raise InvalidDocument("EMPTY_DOCUMENT")
    return output

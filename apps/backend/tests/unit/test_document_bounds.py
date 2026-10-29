from pathlib import Path

import pytest
from pypdf import PdfWriter

from supportdesk.modules.assistant.embeddings.e5 import model
from supportdesk.modules.knowledge.chunking import chunks
from supportdesk.modules.knowledge.parsers import InvalidDocument, parse


def test_pdf_page_limit_and_ocr_boundary(tmp_path: Path):
    path = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.write(path)
    with pytest.raises(InvalidDocument, match="OCR_REQUIRED"):
        parse(path, "application/pdf")
    for _ in range(50):
        writer.add_blank_page(width=200, height=200)
    writer.write(path)
    with pytest.raises(InvalidDocument, match="TOO_MANY_PAGES"):
        parse(path, "application/pdf")


def test_file_byte_limit_and_encoding(tmp_path: Path):
    path = tmp_path / "file.txt"
    path.write_bytes(b"\xff")
    with pytest.raises(InvalidDocument, match="INVALID_ENCODING"):
        parse(path, "text/plain")
    with path.open("wb") as output:
        output.truncate(10 * 1024 * 1024 + 1)
    with pytest.raises(InvalidDocument, match="FILE_TOO_LARGE"):
        parse(path, "text/plain")


def test_real_tokenizer_chunks_fit_e5_window():
    tokenizer = model().tokenizer
    passages = chunks(
        [(1, "# Fixture\n" + ("سلام آزمایش راهنمای وبهوک. " * 500))], tokenizer
    )
    assert len(passages) > 1
    assert all(
        len(tokenizer("passage: " + piece.text)["input_ids"]) <= 512
        for piece in passages
    )
    assert all(piece.token_count <= 350 for piece in passages)

from pathlib import Path


class InvalidDocument(Exception):
    pass


def parse(path: Path, content_type: str) -> list[tuple[int, str]]:
    if path.stat().st_size > 10 * 1024 * 1024:
        raise InvalidDocument("FILE_TOO_LARGE")
    if content_type == "application/pdf":
        from pypdf import PdfReader

        reader = PdfReader(path, strict=True)
        if reader.is_encrypted:
            raise InvalidDocument("ENCRYPTED_PDF")
        if len(reader.pages) > 50:
            raise InvalidDocument("TOO_MANY_PAGES")
        pages = []
        total = 0
        for index, page in enumerate(reader.pages):
            # Bound decompression before pypdf text extraction.
            contents = page.get_contents()
            if contents and len(contents.get_data()) > 4 * 1024 * 1024:
                raise InvalidDocument("PAGE_TOO_COMPLEX")
            text = page.extract_text() or ""
            total += len(text)
            if total > 1_000_000:
                raise InvalidDocument("EXTRACTED_TEXT_TOO_LARGE")
            pages.append((index + 1, text))
        if sum(len(text.strip()) for _, text in pages) < 20:
            raise InvalidDocument("OCR_REQUIRED")
        return pages
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeError as exc:
        raise InvalidDocument("INVALID_ENCODING") from exc
    if not text.strip() or "\x00" in text:
        raise InvalidDocument("INVALID_TEXT")
    return [(1, text)]

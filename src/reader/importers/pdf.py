from __future__ import annotations

from pathlib import Path

from ..models import Format, ParsedBook
from .txt import _split_chapters


def parse_pdf(path: Path) -> ParsedBook:
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover
        raise ValueError("PDF требует установки pypdf: uv add pypdf") from e

    reader = PdfReader(str(path))
    text_parts: list[str] = []
    for page in reader.pages:
        try:
            page_text = page.extract_text() or ""
        except Exception:  # noqa: BLE001
            page_text = ""
        if page_text:
            text_parts.append(page_text)
    meta = reader.metadata
    title = (meta.title if meta and meta.title else "").strip() or path.stem
    return ParsedBook(
        format=Format.PDF,
        title=title,
        chapters=_split_chapters("\n".join(text_parts)),
    )
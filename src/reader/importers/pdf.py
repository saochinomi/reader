from __future__ import annotations

from pathlib import Path

from ..models import Format, ParsedBook
from .txt import _split_chapters


def parse_pdf(path: Path) -> ParsedBook:
    """Извлекает текст из PDF. Основной путь - PyMuPDF, он в десятки раз
    быстрее pypdf; pypdf остаётся запасным вариантом."""
    try:
        import pymupdf  # noqa: PLC0415 - тяжёлый импорт только для PDF
    except ImportError:  # pragma: no cover
        try:
            import fitz as pymupdf  # старые версии PyMuPDF
        except ImportError:
            return _parse_pdf_pypdf(path)

    doc = pymupdf.open(str(path))
    text = "\n".join(page.get_text() for page in doc)
    meta = doc.metadata or {}
    title = (meta.get("title") or "").strip() or path.stem
    return ParsedBook(
        format=Format.PDF,
        title=title,
        chapters=_split_chapters(text),
    )


def _parse_pdf_pypdf(path: Path) -> ParsedBook:
    try:
        from pypdf import PdfReader
    except ImportError as e:  # pragma: no cover
        raise ValueError("PDF требует установки pymupdf или pypdf") from e

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
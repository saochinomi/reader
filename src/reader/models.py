from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator


class Format(str, Enum):
    TXT = "txt"
    EPUB = "epub"
    FB2 = "fb2"
    HTML = "html"
    MARKDOWN = "md"
    RTF = "rtf"
    DOCX = "docx"
    PDF = "pdf"
    MOBI = "mobi"
    DJVU = "djvu"
    DOC = "doc"
    UNKNOWN = "unknown"


@dataclass
class Chapter:
    title: str
    paragraphs: list[str] = field(default_factory=list)


@dataclass
class ParsedBook:
    format: Format
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    language: str | None = None
    description: str = ""
    chapters: list[Chapter] = field(default_factory=list)

    @property
    def text_length(self) -> int:
        return sum(len(p) for ch in self.chapters for p in ch.paragraphs)

    def paragraphs(self) -> Iterator[tuple[int, int, str]]:
        """Итератор (индекс главы, индекс абзаца, текст)."""
        for ci, ch in enumerate(self.chapters):
            for pi, p in enumerate(ch.paragraphs):
                yield ci, pi, p


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

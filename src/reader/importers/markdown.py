from __future__ import annotations

import re
from pathlib import Path

from ..models import Chapter, Format, ParsedBook
from .titles import clean_title

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_RE = re.compile(r"^(\s*)(?:[-*+]\s+|>\s*|\d+[.)]\s*)")


def _split_chapters(text: str) -> list[Chapter]:
    chapters: list[Chapter] = []
    current = Chapter("")
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _HEADING_RE.match(line)
        if m and len(line) < 120:
            if current.paragraphs or current.title:
                chapters.append(current)
            current = Chapter(clean_title(m.group(2)))
            continue
        line = _LIST_RE.sub("", line).strip()
        if line:
            current.paragraphs.append(line)
    if current.paragraphs or current.title:
        chapters.append(current)
    if not chapters:
        chapters.append(Chapter(""))
    return chapters


def parse_markdown(path: Path) -> ParsedBook:
    text = path.read_text(encoding="utf-8", errors="replace")
    return ParsedBook(
        format=Format.MARKDOWN,
        title=path.stem,
        chapters=_split_chapters(text),
    )
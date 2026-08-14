from __future__ import annotations

import re
from pathlib import Path

from charset_normalizer import from_path

from ..models import Chapter, Format, ParsedBook

_BLANK_RE = re.compile(r"[ \t\u00a0]+")
_CHAPTER_RE = re.compile(r"^(?:\s*)(?:ГЛАВА|Chapter|Глава)\s*[IVXLC\d\s]+\.?[:\s]*(.*)$", re.IGNORECASE)


def _split_chapters(text: str) -> list[Chapter]:
    lines: list[str] = []
    for raw in text.splitlines():
        line = _BLANK_RE.sub(" ", raw).strip()
        if line:
            lines.append(line)

    chapters: list[Chapter] = []
    current = Chapter("")
    for line in lines:
        m = _CHAPTER_RE.match(line)
        if m and len(line) < 120:
            if current.paragraphs or current.title:
                chapters.append(current)
            current = Chapter(m.group(1).strip() or line.strip())
        else:
            current.paragraphs.append(line)
    if current.paragraphs or current.title:
        chapters.append(current)
    if not chapters:
        chapters.append(Chapter(""))
    return chapters


def parse_txt(path: Path) -> ParsedBook:
    matches = from_path(path)
    best = matches.best()
    encoding = best.encoding if best else "utf-8"
    text = str(best) if best else path.read_text(encoding="utf-8", errors="replace")

    title = path.stem
    chapters = _split_chapters(text)
    return ParsedBook(
        format=Format.TXT,
        title=title,
        chapters=chapters,
    )

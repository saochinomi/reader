from __future__ import annotations

from pathlib import Path

from lxml import etree

from ..models import Chapter, Format, ParsedBook
from .titles import clean_title

_SKIP_TAGS = {"script", "style", "head", "nav", "noscript"}
_HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
_PARAGRAPH_TAGS = {"p", "li", "blockquote", "td", "dt", "dd", "pre"}


def _local(elem) -> str:
    return elem.tag.split("}")[-1].lower() if isinstance(elem.tag, str) else ""


def _text_of(elem) -> str:
    return " ".join(elem.itertext()).replace("\xa0", " ").strip()


def _iter_blocks(root) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    for el in root.iter():
        local = _local(el)
        if local in _SKIP_TAGS:
            continue
        if local in _HEADING_TAGS:
            text = _text_of(el)
            if text:
                blocks.append(("h", text))
        elif local in _PARAGRAPH_TAGS:
            text = _text_of(el)
            if text:
                blocks.append(("p", text))
        elif local == "div":
            text = _text_of(el)
            if text and not any(
                _local(c) in _HEADING_TAGS | _PARAGRAPH_TAGS for c in el.iter()
            ):
                blocks.append(("p", text))
    return blocks


def _build_chapters(blocks: list[tuple[str, str]]) -> list[Chapter]:
    chapters: list[Chapter] = []
    current = Chapter("")
    for kind, text in blocks:
        if kind == "h":
            if current.paragraphs or current.title:
                chapters.append(current)
            current = Chapter(clean_title(text))
        else:
            current.paragraphs.append(text)
    if current.paragraphs or current.title:
        chapters.append(current)
    if not chapters:
        chapters.append(Chapter(""))
    return chapters


def parse_html(path: Path) -> ParsedBook:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        from charset_normalizer import from_bytes

        best = from_bytes(raw).best()
        text = str(best) if best else raw.decode("utf-8", errors="replace")
    root = etree.fromstring(text.encode("utf-8"), parser=etree.HTMLParser(recover=True))
    title_el = root.find(".//title")
    title = _text_of(title_el) if title_el is not None else path.stem
    first_h = next((t for k, t in _iter_blocks(root) if k == "h"), None)
    if not title:
        title = first_h or path.stem
    return ParsedBook(
        format=Format.HTML,
        title=title,
        chapters=_build_chapters(_iter_blocks(root)),
    )
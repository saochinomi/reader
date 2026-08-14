from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

from ..models import Chapter, Format, ParsedBook

def _local(elem) -> str:
    return elem.tag.split("}")[-1].lower() if isinstance(elem.tag, str) else ""


def _text_of(elem) -> str:
    return " ".join(elem.itertext()).strip() if elem is not None else ""


def _first(elem, name: str):
    return next((c for c in elem.iter() if _local(c) == name), None)


def _parse_fb2(root: etree._Element) -> ParsedBook:
    book = ParsedBook(format=Format.FB2, title="Без названия")

    title_info = _first(root, "title-info")
    if title_info is not None:
        book.title = _text_of(_first(title_info, "book-title")) or book.title
        for author in [c for c in title_info if _local(c) == "author"]:
            if not isinstance(author.tag, str):
                continue
            firstname = _text_of(next((c for c in author if _local(c) == "first-name"), None))
            middlename = _text_of(next((c for c in author if _local(c) == "middle-name"), None))
            lastname = _text_of(next((c for c in author if _local(c) == "last-name"), None))
            name = " ".join(filter(None, (firstname, middlename, lastname)))
            if name:
                book.authors.append(name)
        date_el = _first(title_info, "date")
        if date_el is not None and date_el.text:
            digits = "".join(ch for ch in date_el.text if ch.isdigit())
            if len(digits) >= 4:
                book.year = int(digits[:4])
        lang_el = _first(title_info, "lang")
        if lang_el is not None and lang_el.text:
            book.language = lang_el.text.strip()
        ann_el = _first(title_info, "annotation")
        if ann_el is not None:
            book.description = _text_of(ann_el)

    def extract_chapters(body) -> list[Chapter]:
        chapters: list[Chapter] = []
        for sec in [e for e in body.iter() if _local(e) == "section"]:
            title_el = next((c for c in sec if _local(c) == "title"), None)
            title = _text_of(title_el)
            paragraphs = []
            for p in sec.iter():
                if _local(p) != "p":
                    continue
                text = _text_of(p)
                if not text:
                    continue
                parent = p.getparent()
                inside_nested = False
                while parent is not None and parent is not sec:
                    if _local(parent) in ("section", "title"):
                        inside_nested = True
                        break
                    parent = parent.getparent()
                if not inside_nested:
                    paragraphs.append(text)
            chapters.append(Chapter(title=title, paragraphs=paragraphs))
        return chapters

    for body in [e for e in root.iter() if _local(e) == "body"]:
        book.chapters.extend(extract_chapters(body))

    # Если глав нет — берём все абзацы в одну главу
    if not book.chapters:
        paras = [p.text.strip() for p in root.iter() if _local(p) == "p" and p.text and p.text.strip()]
        if paras:
            book.chapters.append(Chapter("", paras))
    return book


def parse_fb2(path: Path) -> ParsedBook:
    raw = path.read_bytes()
    if raw[:2] == b"PK":
        with zipfile.ZipFile(path) as zf:
            name = next((n for n in zf.namelist() if n.lower().endswith(".fb2")), None)
            if name is None:
                raise ValueError("FB2.zip: внутри нет .fb2")
            raw = zf.read(name)
    root = etree.fromstring(raw)
    return _parse_fb2(root)

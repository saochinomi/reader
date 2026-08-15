from __future__ import annotations

import zipfile
from pathlib import Path

from lxml import etree

from ..models import Chapter, Format, ParsedBook
from .titles import clean_title

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_DC = "{http://purl.org/dc/elements/1.1/}"
_CP = "{http://schemas.openxmlformats.org/package/2006/metadata/core-properties}"


def _local(elem) -> str:
    return elem.tag.split("}")[-1].lower() if isinstance(elem.tag, str) else ""


def parse_docx(path: Path) -> ParsedBook:
    with zipfile.ZipFile(path) as zf:
        doc = zf.read("word/document.xml")
        try:
            core = etree.fromstring(zf.read("docProps/core.xml"))
        except (KeyError, etree.XMLSyntaxError):
            core = None
    root = etree.fromstring(doc)

    title = ""
    authors = []
    if core is not None:
        t = next((el.text for el in core.iter() if el.tag == _DC + "title" and el.text), None)
        if t:
            title = t.strip()
        for el in core.iter():
            if el.tag == _DC + "creator" and el.text:
                authors.append(el.text.strip())

    chapters: list[Chapter] = []
    current = Chapter("")
    for p in root.iter(_W + "p"):
        style = next(
            (el.get(_W + "val") for el in p.iter() if el.tag == _W + "pStyle"), None
        )
        text = "".join(p.itertext()).replace("\xa0", " ").strip()
        if not text:
            continue
        if style and style.lower().startswith("heading"):
            if current.paragraphs or current.title:
                chapters.append(current)
            current = Chapter(clean_title(text))
        else:
            current.paragraphs.append(text)
    if current.paragraphs or current.title:
        chapters.append(current)
    if not chapters:
        chapters.append(Chapter(""))

    return ParsedBook(
        format=Format.DOCX,
        title=title or path.stem,
        authors=authors,
        chapters=chapters,
    )
from __future__ import annotations

import re
import zipfile
from html import unescape
from pathlib import Path
from urllib.parse import unquote

from lxml import etree

from ..models import Chapter, Format, ParsedBook

_XHTML_NS = "http://www.w3.org/1999/xhtml"

_WHITESPACE_RE = re.compile(r"\s+")

_BLOCK_TAGS = {
    "p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
    "li", "dd", "dt", "tr", "pre", "section", "header", "footer", "hr",
}

_SKIP_TAGS = {"head", "title", "script", "style", "h1", "h2", "h3", "h4", "h5", "h6"}


def _local(elem) -> str:
    return elem.tag.split("}")[-1].lower() if isinstance(elem.tag, str) else ""


def _href_of(nav: str, target: str) -> str:
    return nav.replace("\\", "/").rsplit("/", 1)[0] + "/" + target.lstrip("/")


def _iter_paragraphs(elem) -> list[str]:
    """Текст документа с сохранением структуры абзацев."""
    parts: list[str] = []
    for e in elem.iter():
        local = _local(e)
        if local in _SKIP_TAGS:
            continue
        if local == "br":
            parts.append("\n")
            continue
        if e.text:
            parts.append(e.text)
        for child in e:
            if child.tail:
                parts.append(child.tail)
        if local in _BLOCK_TAGS:
            parts.append("\n")
    text = "".join(parts)
    return [
        p.strip()
        for t in text.split("\n")
        for p in [_WHITESPACE_RE.sub(" ", t).strip()]
        if p
    ]


class EpubParser:
    def __init__(self, path: Path):
        self._path = path

    def parse(self) -> ParsedBook:
        with zipfile.ZipFile(self._path) as zf:
            container = _find_container_path(zf)
            if not container:
                raise ValueError("EPUB: нет META-INF/container.xml")
            opf_xml = etree.fromstring(zf.read(container))
            book = self._metadata(zf, opf_xml, container)
            spine = self._spine(opf_xml, container)
            nav = self._nav_targets(zf, container, opf_xml)
            book.chapters = self._chapters(zf, spine, nav)
            if not book.chapters:
                raise ValueError("EPUB: в книге нет контента")
            return book

    def _metadata(self, zf, opf_xml, container: str) -> ParsedBook:
        book = ParsedBook(format=Format.EPUB, title=self._path.stem)
        title = ""
        authors: list[str] = []
        metadata = next(
            (e for e in opf_xml.iter() if _local(e) == "metadata"),
            opf_xml,
        )
        for elem in metadata:
            if not isinstance(elem.tag, str):
                continue
            tag = _local(elem)
            text = str(elem.text or "").strip()
            if not text:
                continue
            if tag == "title" and not title:
                title = text
            elif tag == "creator":
                authors.append(text)
            elif tag == "language" and book.language is None:
                book.language = text
            elif tag == "date" and book.year is None:
                m = re.search(r"\d{4}", text)
                if m:
                    book.year = int(m.group())
            elif tag == "meta" and not book.description:
                name = (elem.get("name") or "").lower()
                if name in ("description", "dc:description"):
                    book.description = unescape(text)
        book.title = title or book.title
        book.authors = authors
        return book

    def _spine(self, opf_xml, container: str) -> list[tuple[str, str]]:
        items = {
            e.get("id"): e
            for e in opf_xml.iter()
            if _local(e) == "item" and e.get("id")
        }
        spine: list[tuple[str, str]] = []
        for r in opf_xml.iter():
            if _local(r) != "itemref":
                continue
            item = items.get(r.get("idref"))
            if item is None:
                continue
            href = item.get("href", "")
            spine.append((href, _href_of(container, unquote(href))))
        return spine

    def _nav_targets(self, zf, container: str, opf_xml) -> dict[str, str]:
        """Названия глав из nav (EPUB3) или NCX (EPUB2)."""
        hrefs: dict[str, str] = {}
        for elem in opf_xml.iter():
            if _local(elem) != "item":
                continue
            media = elem.get("media-type", "")
            href = elem.get("href", "")
            if media not in ("application/x-dtbncx+xml", "application/xhtml+xml") and elem.get(
                "properties"
            ) != "nav":
                continue
            abs_href = _href_of(container, unquote(href))
            try:
                content = zf.read(abs_href)
            except KeyError:
                continue
            try:
                root = etree.fromstring(content)
            except etree.XMLSyntaxError:
                continue
            if media == "application/x-dtbncx+xml":
                for navpoint in root.iter():
                    if _local(navpoint) != "navpoint":
                        continue
                    label_el = navpoint.find(f".//{{{_XHTML_NS}}}text")
                    if label_el is None:
                        continue
                    label = " ".join(label_el.itertext()).strip()
                    content_el = next(
                        (c for c in navpoint if _local(c) == "content"), None
                    )
                    if content_el is not None and label:
                        hrefs.setdefault(content_el.get("src", "").split("#")[0], label)
            else:
                for li in root.iter():
                    if _local(li) != "li":
                        continue
                    a = li.find(f".//{{{_XHTML_NS}}}a")
                    if a is None:
                        continue
                    label = " ".join(a.itertext()).strip()
                    if label:
                        hrefs.setdefault(a.get("href", "").split("#")[0], label)
        return hrefs

    def _chapters(self, zf, spine, nav) -> list[Chapter]:
        chapters: list[Chapter] = []
        for href, abs_href in spine:
            try:
                content = zf.read(abs_href)
                root = etree.fromstring(content)
            except (KeyError, etree.XMLSyntaxError):
                continue
            h_text = ""
            for h in root.iter():
                if _local(h) in ("h1", "h2", "h3", "h4", "h5", "h6", "title"):
                    t = " ".join(h.itertext()).strip()
                    if t:
                        h_text = t
                        break
            paragraphs = _iter_paragraphs(root)
            if not paragraphs and not h_text:
                continue
            chapters.append(Chapter(title=nav.get(href, h_text), paragraphs=paragraphs))
        return chapters


def _find_container_path(zf: zipfile.ZipFile) -> str:
    try:
        root = etree.fromstring(zf.read("META-INF/container.xml"))
    except (KeyError, etree.XMLSyntaxError):
        return ""
    for elem in root.iter():
        if _local(elem) == "rootfile":
            return str(elem.get("full-path", ""))
    return ""


def parse_epub(path: Path) -> ParsedBook:
    return EpubParser(path).parse()

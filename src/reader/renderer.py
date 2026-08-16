from __future__ import annotations

from dataclasses import dataclass

from .models import ParsedBook

HEADER_LINES = 3


@dataclass
class Page:
    lines: list[str]
    meta: list[tuple[int, int, int]]
    chapter_index: int
    paragraph_index: int  # первый абзац на странице


class BookRenderer:
    """Постраничный рендер книги под размер терминала."""

    def __init__(self, book: ParsedBook, width: int = 80, height: int = 40):
        self.book = book
        self.width = max(20, width)
        self.height = max(5, height)
        self._pages: list[tuple[int, int]] = []
        self._build()

    def _line_count(self, text: str) -> int:
        return max(1, (len(text) + self.width - 1) // self.width)

    def _build(self) -> None:
        pages: list[tuple[int, int]] = []
        start_ci, start_pi = 0, 0
        used = 0
        limit = self.height - HEADER_LINES
        for ci, pi, text in self.book.paragraphs():
            n = self._line_count(text)
            if used and used + n > limit:
                pages.append((start_ci, start_pi))
                start_ci, start_pi = ci, pi
                used = n
            else:
                used += n
        if used or not pages:
            pages.append((start_ci, start_pi))
        self._pages = pages

    def page_count(self) -> int:
        return len(self._pages)

    def render(self, page_index: int) -> Page:
        page_index = max(0, min(page_index, self.page_count() - 1))
        ci, pi = self._pages[page_index]
        lines: list[str] = []
        meta: list[tuple[int, int, int]] = []
        used = 0
        limit = self.height - HEADER_LINES
        for pci, ppi, text in self.book.paragraphs():
            if (pci, ppi) < (ci, pi):
                continue
            if used and used + self._line_count(text) > limit:
                break
            for w, off in _wrap(text, self.width):
                lines.append(w)
                meta.append((pci, ppi, off))
            lines.append("")
            meta.append((pci, ppi, len(text)))
            used += self._line_count(text) + 1
        return Page(lines=lines, meta=meta, chapter_index=ci, paragraph_index=pi)

    def locate(self, chapter: int, paragraph: int) -> int:
        """Страница, на которой начинается абзац."""
        for i, (ci, pi) in enumerate(self._pages):
            if ci > chapter or (ci == chapter and pi >= paragraph):
                return i
        return len(self._pages) - 1

    def locate_offset(self, chapter: int, paragraph: int, offset: int) -> int:
        """Страница, на которой видна позиция (глава, абзац, смещение)."""
        page = self.locate(chapter, paragraph)
        for _ in range(4):
            if page >= self.page_count():
                return self.page_count() - 1
            for mci, mpi, moff in self.render(page).meta:
                if (mci, mpi) == (chapter, paragraph) and moff <= offset:
                    return page
            page += 1
        return page - 1


def _wrap(text: str, width: int) -> list[tuple[str, int]]:
    if len(text) <= width:
        return [(text, 0)]
    out: list[tuple[str, int]] = []
    rest, off = text, 0
    while len(rest) > width:
        cut = rest.rfind(" ", 0, width)
        if cut < width // 2:
            cut = width
        out.append((rest[:cut], off))
        stripped = rest[cut:].lstrip()
        off += len(rest) - len(stripped)
        rest = stripped
    out.append((rest, off))
    return out
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Static

from ..db import LibraryDB
from ..models import ParsedBook
from ..renderer import BookRenderer
from .bookmarks_screen import BookmarksScreen
from .help_screen import HelpScreen
from .status_bar import StatusBar

_WIDTH_MODES = (1.0, 0.8, 0.65)


class ReaderScreen(Screen):
    BINDINGS = [
        Binding("j,down,space", "next_page", "След. стр."),
        Binding("k,up,backspace", "prev_page", "Пред. стр."),
        Binding("n", "next_chapter", "След. глава"),
        Binding("p", "prev_chapter", "Пред. глава"),
        Binding("s", "add_bookmark", "Закладка"),
        Binding("b", "show_bookmarks", "Закладки"),
        Binding("f", "cycle_width", "Ширина"),
        Binding("?", "show_help", "Помощь"),
        Binding("escape,q", "back", "Назад"),
    ]

    def __init__(self, db: LibraryDB, book_id: int):
        super().__init__()
        self.db = db
        self.book_id = book_id
        self.book: ParsedBook | None = None
        self.renderer: BookRenderer | None = None
        self.page_index = 0
        self.width_mode = 0

    def compose(self) -> ComposeResult:
        yield Static(id="chapter")
        yield Static(id="content")
        yield StatusBar(id="statusbar")

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def on_mount(self) -> None:
        self.book = self.app.get_book(self.book_id)
        self._rebuild_renderer()
        row = self.db.get_progress(self.book_id)
        if row is not None:
            self.page_index = self.renderer.locate(row["chapter"], row["paragraph"])
        self._draw()

    def _rebuild_renderer(self) -> None:
        assert self.book is not None
        mode = _WIDTH_MODES[self.width_mode]
        width = max(20, int((self.size.width - 2) * mode))
        height = max(5, self.size.height - 2)
        if self.renderer is None:
            self.renderer = BookRenderer(self.book, width=width, height=height)
            return
        current = self.renderer.render(self.page_index)
        self.renderer = BookRenderer(self.book, width=width, height=height)
        self.page_index = self.renderer.locate(current.chapter_index, current.paragraph_index)

    def _draw(self) -> None:
        assert self.book is not None and self.renderer is not None
        page = self.renderer.render(self.page_index)
        title = self.book.chapters[page.chapter_index].title or "…"
        self.query_one("#chapter", Static).update(f"[bold]#9ece6a{title}[/bold]")
        self.query_one("#content", Static).update("\n".join(page.lines) if page.lines else "…")
        total = self.renderer.page_count()
        pct = round((self.page_index + 1) * 100 / total) if total else 0
        self.query_one("#statusbar", StatusBar).read(
            self.book.title,
            chapter=f"гл. {page.chapter_index + 1}/{len(self.book.chapters)}",
            page=f"стр. {self.page_index + 1}/{total}",
            fmt=self.book.format.value.upper(),
            pct=pct,
        )
        self._save_progress(page.chapter_index, page.paragraph_index)

    def _save_progress(self, chapter: int, paragraph: int) -> None:
        self.db.save_progress(self.book_id, chapter, paragraph, self.page_index)

    def on_resize(self) -> None:
        if self.renderer is not None:
            self._rebuild_renderer()
            self._draw()

    # --- действия ---

    def action_next_page(self) -> None:
        if self.renderer and self.page_index < self.renderer.page_count() - 1:
            self.page_index += 1
            self._draw()

    def action_prev_page(self) -> None:
        if self.page_index > 0:
            self.page_index -= 1
            self._draw()

    def action_next_chapter(self) -> None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        if page.chapter_index < len(self.book.chapters) - 1:
            self.page_index = self.renderer.locate(page.chapter_index + 1, 0)
            self._draw()

    def action_prev_chapter(self) -> None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        if page.chapter_index > 0:
            self.page_index = self.renderer.locate(page.chapter_index - 1, 0)
            self._draw()

    def action_cycle_width(self) -> None:
        self.width_mode = (self.width_mode + 1) % len(_WIDTH_MODES)
        self._rebuild_renderer()
        self._draw()

    def action_add_bookmark(self) -> None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        note = (page.lines[0] if page.lines else "")[:60]
        self.db.add_bookmark(self.book_id, page.chapter_index, page.paragraph_index, note)
        self.app.notify("Закладка добавлена", severity="information")

    def action_show_bookmarks(self) -> None:
        assert self.renderer is not None
        bookmarks = self.db.bookmarks(self.book_id)
        if not bookmarks:
            self.app.notify("Закладок нет (s — добавить)", severity="information")
            return
        self.app.push_screen(
            BookmarksScreen(self.book_id, bookmarks, self._on_bookmark_deleted),
            self._on_bookmark_selected,
        )

    def _on_bookmark_selected(self, bookmark_id: int | None) -> None:
        if bookmark_id is None:
            return
        assert self.renderer is not None
        for bm in self.db.bookmarks(self.book_id):
            if bm["id"] == bookmark_id:
                self.page_index = self.renderer.locate(bm["chapter"], bm["paragraph"])
                self._draw()
                break

    def _on_bookmark_deleted(self, bookmark_id: int) -> None:
        pass

    def action_back(self) -> None:
        self.app.pop_screen()
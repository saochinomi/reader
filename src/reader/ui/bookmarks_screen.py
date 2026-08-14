from __future__ import annotations

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Label, OptionList, Static
from textual.widgets.option_list import Option


class BookmarksScreen(Screen[Optional[int]]):
    """Список закладок книги. Возвращает id закладки при выборе."""

    BINDINGS = [
        Binding("escape", "close", "Закрыть"),
        Binding("delete", "delete", "Удалить"),
        Binding("d", "delete", "Удалить"),
    ]

    def __init__(self, book_id: int, bookmarks, on_deleted):
        super().__init__()
        self.book_id = book_id
        self.bookmarks = bookmarks
        self.on_deleted = on_deleted

    def compose(self) -> ComposeResult:
        yield Static("Закладки — Enter: перейти, Delete: удалить, Esc: закрыть", id="bookmark_title")
        yield OptionList(id="list")
        yield Footer()

    def on_mount(self) -> None:
        self._fill()
        self.query_one("#list", OptionList).focus()

    def _fill(self) -> None:
        ol = self.query_one("#list", OptionList)
        ol.clear_options()
        self.bookmarks = self.app.db.bookmarks(self.book_id)
        for i, bm in enumerate(self.bookmarks, 1):
            ol.add_option(
                Option(f"{i}. стр. {bm['paragraph']} · гл. {bm['chapter'] + 1} — {bm['note'] or '…'}", id=str(bm["id"]))
            )
        if self.bookmarks:
            ol.highlighted = 0

    def action_close(self) -> None:
        self.dismiss(None)

    @on(OptionList.OptionSelected)
    def _on_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id is not None:
            self.dismiss(int(event.option.id))

    def action_delete(self) -> None:
        ol = self.query_one("#list", OptionList)
        option = ol.highlighted_option
        if option is None or option.id is None:
            return
        bookmark_id = int(option.id)
        self.app.db.remove_bookmark(bookmark_id)
        if self.on_deleted:
            self.on_deleted(bookmark_id)
        self._fill()
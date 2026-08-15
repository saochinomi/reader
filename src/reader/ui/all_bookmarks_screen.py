from __future__ import annotations

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option


class AllBookmarksScreen(Screen[Optional[tuple[int, int, int]]]):
    """Закладки всех книг. Возвращает (book_id, chapter, paragraph) при выборе."""

    BINDINGS = [
        Binding("escape,q", "close", "Закрыть"),
        Binding("delete,d", "delete", "Удалить"),
    ]

    def __init__(self):
        super().__init__()
        self._map: dict[str, tuple[int, int, int]] = {}

    def compose(self) -> ComposeResult:
        yield Static("Закладки всех книг — Enter: открыть, Delete: удалить, Esc: закрыть", id="bookmark_title")
        yield OptionList(id="list")

    def on_mount(self) -> None:
        self._fill()
        self.query_one("#list", OptionList).focus()

    def _fill(self) -> None:
        ol = self.query_one("#list", OptionList)
        ol.clear_options()
        self._map.clear()
        for bm in self.app.db.all_bookmarks():
            key = str(bm["id"])
            self._map[key] = (bm["book_id"], bm["chapter"], bm["paragraph"])
            ol.add_option(
                Option(
                    f"{bm['book_title']} · гл. {bm['chapter'] + 1} — {bm['note'] or '…'}",
                    id=key,
                )
            )
        if self._map:
            ol.highlighted = 0
        else:
            ol.add_option(Option("Закладок пока нет (в читалке — s)", id="none", disabled=True))

    def action_close(self) -> None:
        self.dismiss(None)

    @on(OptionList.OptionSelected)
    def _on_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id in self._map:
            self.dismiss(self._map[event.option.id])

    def action_delete(self) -> None:
        ol = self.query_one("#list", OptionList)
        option = ol.highlighted_option
        if option is None or option.id is None or option.id not in self._map:
            return
        self.app.db.remove_bookmark(int(option.id))
        self._fill()
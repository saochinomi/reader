from __future__ import annotations

from typing import Optional

from rich.markup import escape
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, OptionList, Static
from textual.widgets.option_list import Option

from .highlight_colors import HIGHLIGHT_COLORS

_JUMP = tuple[int, int, int, int]


class NotesScreen(Screen[Optional[_JUMP]]):
    """Заметки по книгам. Без book_id - список книг, с ним - фрагменты книги."""

    BINDINGS = [
        Binding("escape", "close", "Закрыть"),
        Binding("delete", "delete", "Удалить"),
        Binding("d", "delete", "Удалить"),
    ]

    def __init__(self, book_id: int | None = None):
        super().__init__()
        self.book_id = book_id

    def compose(self) -> ComposeResult:
        if self.book_id is None:
            yield Static(
                "Заметки по книгам - Enter: открыть · Esc: закрыть", id="bookmark_title"
            )
        else:
            yield Static(
                "Заметки книги - Enter: перейти · D: удалить · Esc: назад", id="bookmark_title"
            )
        yield OptionList(id="list")
        yield Footer()

    def on_mount(self) -> None:
        self._fill()
        self.query_one("#list", OptionList).focus()

    def _fill(self) -> None:
        ol = self.query_one("#list", OptionList)
        ol.clear_options()
        if self.book_id is None:
            for row in self.app.db.highlights_books():
                ol.add_option(
                    Option(f"{row['title']} - {row['n']}", id=f"b{row['id']}")
                )
        else:
            for i, h in enumerate(self.app.db.highlights(self.book_id), 1):
                color = HIGHLIGHT_COLORS.get(h["color"], "on #3a3a3a")
                text = (h["text"] or "…").replace("\n", " ")
                ol.add_option(
                    Option(
                        f"[{color}]▪[/] {escape(text[:60])} · гл. {h['chapter_s'] + 1}",
                        id=f"h{h['id']}",
                    )
                )
        if ol.option_count:
            ol.highlighted = 0

    def action_close(self) -> None:
        self.dismiss(None)

    def action_delete(self) -> None:
        if self.book_id is None:
            return
        ol = self.query_one("#list", OptionList)
        option = ol.highlighted_option
        if option is None or option.id is None:
            return
        self.app.db.remove_highlight(int(option.id[1:]))
        self._fill()

    @on(OptionList.OptionSelected)
    def _on_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id is None:
            return
        if self.book_id is None:
            self.book_id = int(event.option.id[1:])
            self.query_one("#bookmark_title", Static).update(
                "Заметки книги - Enter: перейти · D: удалить · Esc: назад"
            )
            self._fill()
            return
        highlight_id = int(event.option.id[1:])
        h = next(
            (x for x in self.app.db.highlights(self.book_id) if x["id"] == highlight_id),
            None,
        )
        if h is not None:
            self.dismiss((self.book_id, h["chapter_s"], h["paragraph_s"], h["offset_s"]))
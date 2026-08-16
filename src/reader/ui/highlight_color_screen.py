from __future__ import annotations

from typing import Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, OptionList, Static
from textual.widgets.option_list import Option

from .highlight_colors import HIGHLIGHT_COLORS


class HighlightColorScreen(Screen[Optional[str]]):
    """Выбор цвета для выделенного фрагмента. Возвращает имя цвета."""

    BINDINGS = [
        Binding("escape", "cancel", "Отмена"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Выделение: выберите цвет", id="bookmark_title")
        yield OptionList(id="list")
        yield Footer()

    def on_mount(self) -> None:
        ol = self.query_one("#list", OptionList)
        for name in HIGHLIGHT_COLORS:
            ol.add_option(
                Option(
                    f"[{HIGHLIGHT_COLORS[name]}]  [/]  {name}",
                    id=name,
                )
            )
        ol.highlighted = 0
        ol.focus()

    def action_cancel(self) -> None:
        self.dismiss(None)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id is not None:
            self.dismiss(event.option.id)
from __future__ import annotations

from typing import Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Label, OptionList
from textual.widgets.option_list import Option


class ConfirmScreen(Screen[bool]):
    """Простой диалог подтверждения: Enter — да, Esc — нет."""

    BINDINGS = [Binding("escape", "no", "Нет"), Binding("n", "no", "Нет")]

    def __init__(self, message: str):
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        yield Label(self.message, id="message")
        yield OptionList(id="answer")
        yield Footer()

    def on_mount(self) -> None:
        ol = self.query_one("#answer", OptionList)
        ol.add_option(Option("Да", id="yes"))
        ol.add_option(Option("Нет", id="no"))
        ol.highlighted = 0
        ol.focus()

    @on(OptionList.OptionSelected)
    def _on_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id == "yes")

    def action_no(self) -> None:
        self.dismiss(False)
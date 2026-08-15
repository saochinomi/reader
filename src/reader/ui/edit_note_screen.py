from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Input, Static


class EditNoteScreen(Screen[str | None]):
    """Редактирование заметки закладки: Enter — сохранить, Esc — отмена."""

    BINDINGS = [
        Binding("escape", "dismiss", "Отмена"),
    ]

    def __init__(self, current: str):
        super().__init__()
        self.current = current

    def compose(self) -> ComposeResult:
        yield Static("Заметка к закладке", id="color_title")
        yield Input(value=self.current, placeholder="стр. 1136–1140 · Jcc — Jump if…", id="note_input")

    def on_mount(self) -> None:
        self.query_one("#note_input", Input).focus()

    @on(Input.Submitted, "#note_input")
    def _on_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def action_dismiss(self) -> None:
        self.dismiss(None)
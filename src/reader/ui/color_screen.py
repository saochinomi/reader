from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from . import theme


class ColorScreen(Screen):
    """Меню выбора акцентного цвета."""

    BINDINGS = [
        Binding("escape,q", "dismiss", "Закрыть"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Акцентный цвет", id="color_title")
        current = self.app._accent_name
        options = []
        for label in theme.PALETTES:
            acc, _bright, _bg, _dim = theme.palette(label)
            mark = "●" if label == current else "○"
            options.append(
                Option(f"[{acc}]{mark}[/] {theme.name(label)}", id=label)
            )
        yield OptionList(*options, id="colors")

    def on_mount(self) -> None:
        self.query_one("#colors", OptionList).focus()

    @on(OptionList.OptionSelected, "#colors")
    def _on_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option.id:
            self.app.set_accent(event.option.id)
        self.app.pop_screen()

    def action_dismiss(self) -> None:
        self.app.pop_screen()
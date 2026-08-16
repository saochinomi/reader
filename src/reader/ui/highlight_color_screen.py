from __future__ import annotations

from typing import Optional

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from .highlight_colors import ACTION_COPY, HIGHLIGHT_COLORS

_COLORS = list(HIGHLIGHT_COLORS)


class HighlightColorScreen(Screen[Optional[str]]):
    """Компактное окно выбора цвета для выделенного текста."""

    BINDINGS = [
        Binding("1", "pick_0", "красный"),
        Binding("2", "pick_1", "жёлтый"),
        Binding("3", "pick_2", "зелёный"),
        Binding("4", "pick_3", "синий"),
        Binding("5", "pick_4", "фиолетовый"),
        Binding("c", "copy", "Копировать"),
        Binding("enter", "pick_0", "Выбрать"),
        Binding("escape", "cancel", "Отмена"),
    ]

    def __init__(self, text: str = ""):
        super().__init__()
        self._text = text

    def compose(self) -> ComposeResult:
        with Vertical(id="popup"):
            yield Static(id="popup_text")
            yield Static(id="popup_colors")
            yield Static(id="popup_hint")

    def on_mount(self) -> None:
        snippet = self._text if len(self._text) <= 46 else self._text[:46] + "…"
        self.query_one("#popup_text", Static).update(f"[#8a8a8a]«{escape(snippet)}»[/]")
        swatches = "   ".join(
            f"[{HIGHLIGHT_COLORS[name]}] {i + 1} ▮▮▮ [/]"
            for i, name in enumerate(_COLORS)
        )
        self.query_one("#popup_colors", Static).update(swatches)
        self.query_one("#popup_hint", Static).update("[#5c5c5c]c - копировать · Esc - отмена[/]")

    def _pick(self, index: int) -> None:
        self.dismiss(_COLORS[index])

    def action_pick_0(self) -> None:
        self._pick(0)

    def action_pick_1(self) -> None:
        self._pick(1)

    def action_pick_2(self) -> None:
        self._pick(2)

    def action_pick_3(self) -> None:
        self._pick(3)

    def action_pick_4(self) -> None:
        self._pick(4)

    def action_copy(self) -> None:
        self.dismiss(ACTION_COPY)

    def action_cancel(self) -> None:
        self.dismiss(None)
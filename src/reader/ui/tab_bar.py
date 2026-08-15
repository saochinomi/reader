from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Static

MAX_BUFFERS = 6


class TabBar(Horizontal):
    """Ряд вкладок-буферов (открытые книги) в стиле bufferline."""

    DEFAULT_CSS = """
    TabBar {
        height: 2;
        padding: 0 1;
        align-vertical: middle;
        align-horizontal: center;
    }

    TabBar Button {
        height: 2;
        padding: 0 1;
        border: none;
        background: transparent;
        color: #6a6a6a;
        margin: 0 0 0 1;
        min-width: 10;
        content-align: left middle;
    }

    TabBar Button.-active-tab {
        background: $accent-dim;
        color: $accent;
        text-style: bold;
    }

    TabBar Button.-plus {
        min-width: 2;
        max-width: 2;
        border: none;
        background: transparent;
        color: #6a6a6a;
        content-align: center middle;
        padding: 0;
        margin: 0 0 0 1;
    }

    TabBar Static {
        color: #5c5c5c;
        padding: 0 1;
        text-style: italic;
    }
    """

    def __init__(self, on_open=None, on_add=None):
        super().__init__()
        self._on_open = on_open
        self._on_add = on_add
        self._tabs: list[tuple[int, str]] = []
        self._active: int | None = None
        self._rebuilding = False
        self._rebuild_again = False

    def compose(self) -> ComposeResult:
        yield Static("нет открытых книг — нажми [b]i[/b]", id="tab-empty")

    def refresh_tabs(self, tabs: list[tuple[int, str]], active: int | None) -> None:
        self._tabs = tabs[:MAX_BUFFERS]
        self._active = active
        self.run_worker(self._rebuild())

    async def _rebuild(self) -> None:
        if self._rebuilding:
            self._rebuild_again = True
            return
        self._rebuilding = True
        try:
            while True:
                self._rebuild_again = False
                await self._rebuild_once()
                if not self._rebuild_again:
                    break
        finally:
            self._rebuilding = False

    async def _rebuild_once(self) -> None:
        for widget in list(self.query(Button)):
            await widget.remove()
        empty = self.query("#tab-empty")
        if empty:
            await empty.first().remove()
        await self.mount(Static("нет открытых книг — нажми [b]i[/b]", id="tab-empty"))
        if not self._tabs:
            return
        for book_id, title in self._tabs:
            active = book_id == self._active
            await self.mount(
                Button(
                    self._label(title),
                    id=f"tab-{book_id}",
                    classes="tab -active-tab" if active else "tab",
                )
            )
        await self.mount(Button("+", id="tab-add", classes="plus"))

    def _label(self, title: str) -> str:
        title = title.strip()
        return title if len(title) <= 14 else title[:13] + "…"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "tab-add":
            if self._on_add:
                self._on_add()
            return
        prefix = "tab-"
        if event.button.id and event.button.id.startswith(prefix):
            try:
                book_id = int(event.button.id[len(prefix):])
            except ValueError:
                return
            if self._on_open:
                self._on_open(book_id)
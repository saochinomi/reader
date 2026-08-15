from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Static

from .banner import banner


class SplashScreen(Screen):
    """Экран приветствия: лого по центру, внизу — «нажмите Enter»."""

    BINDINGS = [
        Binding("enter,space", "continue_app", "Продолжить"),
        Binding("q,escape", "quit_app", "Выход"),
    ]

    DEFAULT_CSS = """
    Vertical#splash_middle {
        height: 1fr;
        align: center middle;
    }

    Static#splash_logo {
        color: $accent;
        text-style: bold;
        text-align: center;
    }

    Static#splash_hint {
        height: 1;
        color: #8a8a8a;
        text-align: center;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="splash_middle"):
            yield Static(banner(), id="splash_logo")
        yield Static("Нажмите Enter — начать", id="splash_hint")

    def action_continue_app(self) -> None:
        self.app.pop_screen()

    def action_quit_app(self) -> None:
        self.app.exit()
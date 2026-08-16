from __future__ import annotations

import json
import time
from pathlib import Path

from textual.app import App
from textual.theme import Theme

from ..db import LibraryDB
from ..models import ParsedBook
from . import theme
from .library_screen import LibraryScreen
from .reader_screen import ReaderScreen
from .splash_screen import SplashScreen

CONFIG_DIR = Path.home() / ".config" / "reader"
CONFIG_FILE = CONFIG_DIR / "config.json"

_TIMER_CHOICES = (15, 30, 45, 60, 90)
_DEFAULT_TIMER_MINUTES = 30


def _config_file() -> Path:
    return Path.home() / ".config" / "reader" / "config.json"

CSS = """
$background: #0a0a0a;
$surface: #0a0a0a;
$panel: #101010;
$text: #c8c8c8;
$text-muted: #5c5c5c;
$foreground: #c8c8c8;
$border: #1c1c1c;

Screen {
    background: #0a0a0a;
    color: #c8c8c8;
}

Static {
    background: transparent;
}

Static#banner {
    height: 7;
    color: $accent;
    padding: 1 2 0 2;
    text-align: center;
    text-style: bold;
}

Static#titlebar {
    height: 1;
    color: $text-muted;
    padding: 0 1;
    text-style: bold;
}

Static#hint {
    height: 1;
    color: $text-muted;
    padding: 0 1;
}

Static#help {
    padding: 1 2;
    margin: 1 2;
    background: #0d0d0d;
    border: round #2a2a2a;
}

Static#color_title {
    height: 3;
    padding: 1 2 0 2;
    color: $accent;
    text-style: bold;
}

Footer {
    background: #0d0d0d;
    color: $text-muted;
    height: 1;
}

Footer > .footer--key {
    color: #8a8a8a;
}

Footer > .footer--description {
    color: #4a4a4a;
}

Input {
    border: none;
    background: #141414;
    color: #d0d0d0;
}

Horizontal#main_row {
    height: 1fr;
}

Vertical#main_column {
    height: 1fr;
}

DataTable {
    background: #0a0a0a;
    color: $text;
    padding: 0 1;
}

Horizontal#last_row {
    height: auto;
    margin-top: 1;
    align-horizontal: center;
}

Static#last_book {
    height: auto;
    text-align: center;
    color: $text;
    padding: 0 1;
}

Horizontal#table_row {
    height: 1fr;
    align-horizontal: center;
}

Horizontal#search_row {
    height: 2;
    align-horizontal: center;
}

Horizontal#search_row Input {
    height: 2;
}

DataTable > .datatable--header {
    background: #0d0d0d;
    color: $text-muted;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $accent-bg;
    color: $accent;
    text-style: bold;
}

DataTable > .datatable--odd-row {
    background: #0a0a0a;
}

DataTable > .datatable--even-row {
    background: #0d0d0d;
}

Tree {
    background: #0a0a0a;
    color: $text;
    padding: 0 1;
}

Tree > .tree--cursor {
    background: $accent-bg;
    color: $accent;
    text-style: bold;
}

Tree > .tree--highlight {
    color: #ffffff;
}

OptionList {
    background: #0a0a0a;
    color: $text;
    padding: 0 1;
}

OptionList > .option-list--option {
    background: transparent;
}

OptionList > .option-list--option-highlighted {
    background: $accent-bg;
    color: $accent;
    text-style: bold;
}

Label#message {
    padding: 1;
}

Static#path {
    height: 1;
    color: #8a8a8a;
    padding: 0 1;
    background: #0d0d0d;
}

Static#status {
    height: 1;
    color: $text-muted;
    padding: 0 1;
}

Static#chapter {
    height: 1;
    color: #8a8a8a;
    padding: 0 1;
    text-align: center;
}

Horizontal#content_row {
    height: 1fr;
    align-horizontal: center;
}

Static#content {
    padding: 0 1;
    height: 1fr;
    background: #0a0a0a;
}

Static#bookmark_title {
    height: 1;
    color: $text-muted;
    padding: 0 1;
}
"""


class ReaderApp(App):
    TITLE = "reader"
    SUB_TITLE = ""
    CSS = CSS

    def __init__(self, db_path: Path, open_path: Path | None = None, splash: bool = True):
        super().__init__()
        self.db_path = db_path
        self.db = LibraryDB(db_path)
        self.open_path = open_path
        self._splash = splash
        self._books_cache: dict[int, ParsedBook] = {}
        self._accent_name = self._load_accent()
        self._timer_minutes = self._load_timer_minutes()
        self._timer_left: float = float(self._timer_minutes * 60)
        self._timer_running = False
        self._timer_deadline = 0.0
        self._register_themes()
        self.theme = f"reader-{self._accent_name}"


    @staticmethod
    def _read_config() -> dict:
        try:
            return json.loads(_config_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    @staticmethod
    def _load_accent() -> str:
        name = ReaderApp._read_config().get("accent", theme.DEFAULT)
        if name in theme.PALETTES:
            return name
        return theme.DEFAULT

    @staticmethod
    def _load_timer_minutes() -> int:
        try:
            minutes = int(ReaderApp._read_config().get("timer_minutes", _DEFAULT_TIMER_MINUTES))
            if 5 <= minutes <= 180:
                return minutes
        except (TypeError, ValueError):
            pass
        return _DEFAULT_TIMER_MINUTES

    def _save_config(self) -> None:
        try:
            path = _config_file()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(
                    {"accent": self._accent_name, "timer_minutes": self._timer_minutes},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _register_themes(self) -> None:
        for label, (acc, bright, bg, dim) in theme.PALETTES.items():
            self.register_theme(
                Theme(
                    name=f"reader-{label}",
                    primary=acc,
                    accent=bright,
                    secondary=bg,
                    success=bright,
                    warning="#e0af68",
                    error="#f7768e",
                    background="#0a0a0a",
                    surface="#0d0d0d",
                    panel="#101010",
                    foreground="#c8c8c8",
                    variables={"accent-bg": bg, "accent-dim": dim},
                )
            )

    def accent_colors(self) -> tuple[str, str, str, str]:
        return theme.palette(self._accent_name)

    def set_accent(self, name: str) -> None:
        if name not in theme.PALETTES or name == self._accent_name:
            return
        self._accent_name = name
        self.theme = f"reader-{name}"
        self._save_config()


    def timer_choices(self) -> tuple[int, ...]:
        return _TIMER_CHOICES

    def timer_minutes(self) -> int:
        return self._timer_minutes

    def timer_running(self) -> bool:
        return self._timer_running

    def timer_left_seconds(self) -> float:
        return self._timer_left

    def set_timer_minutes(self, minutes: int) -> None:
        if minutes not in _TIMER_CHOICES:
            return
        self._timer_minutes = minutes
        self._timer_left = float(minutes * 60)
        self._timer_running = False
        self._save_config()

    def timer_start_pause(self) -> None:
        if self._timer_running:
            self._timer_left = max(0.0, self._timer_deadline - time.monotonic())
            self._timer_running = False
            return
        if self._timer_left <= 0:
            self._timer_left = float(self._timer_minutes * 60)
        self._timer_deadline = time.monotonic() + self._timer_left
        self._timer_running = True

    def timer_reset(self) -> None:
        self._timer_left = float(self._timer_minutes * 60)
        self._timer_running = False

    def timer_tick(self) -> None:
        if not self._timer_running:
            return
        self._timer_left = max(0.0, self._timer_deadline - time.monotonic())
        if self._timer_left <= 0:
            self._timer_running = False
            self.notify("⏳ Время чтения вышло - отдохните!", severity="warning")

    def timer_text(self) -> str:
        total = self._timer_minutes * 60
        left = int(self._timer_left + 0.999)
        mm, ss = divmod(left, 60)
        icon = "⏳" if self._timer_running or left >= total else "⏸"
        return f"{icon} {mm:02d}:{ss:02d}"

    def on_mount(self) -> None:
        books_dir = Path.home() / "Books"
        books_dir.mkdir(parents=True, exist_ok=True)
        if self.open_path is not None and self.open_path.is_dir():
            self.push_screen(LibraryScreen(self.db, import_dir=str(self.open_path)))
        else:
            self.push_screen(LibraryScreen(self.db))
        if self.open_path is not None and self.open_path.is_file():
            try:
                from ..library import import_book

                book_id = import_book(self.db, self.open_path)
                self.push_screen(ReaderScreen(self.db, book_id))
            except Exception as e:  # noqa: BLE001
                self.call_after_refresh(
                    self.notify,
                    f"Не удалось открыть «{self.open_path.name}»: {e}",
                    severity="error",
                )
        if self._splash:
            self.push_screen(SplashScreen())

    def get_book(self, book_id: int) -> ParsedBook:
        if book_id not in self._books_cache:
            row = self.db.get_book(book_id)
            if row is None:
                raise KeyError(f"Книга {book_id} не найдена в БД")
            from ..cache import load_or_parse

            self._books_cache[book_id] = load_or_parse(self.db, Path(row["path"]))
        return self._books_cache[book_id]
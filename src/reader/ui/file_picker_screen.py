from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DirectoryTree, Footer, Static

BOOK_EXTENSIONS = {".txt", ".epub", ".fb2", ".zip"}


class BookDirectoryTree(DirectoryTree):
    """Дерево, показывающее только книги и папки."""

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        for p in paths:
            if p.is_dir() or p.suffix.lower() in BOOK_EXTENSIONS:
                yield p


class FilePickerScreen(Screen[Path]):
    """Файловый менеджер для выбора книги."""

    BINDINGS = [
        Binding("escape", "close", "Отмена"),
        Binding("h", "go_home", "Домой"),
        Binding("b", "go_books", "~/Books"),
        Binding("l", "go_last", "Последняя папка"),
    ]

    def __init__(self, start: Path | None = None):
        super().__init__()
        self.last_dir: Path | None = None
        start = start or Path.home()
        self._start = start if start.is_dir() else Path.home()

    def compose(self) -> ComposeResult:
        yield Static(id="path")
        yield BookDirectoryTree(str(self._start), id="tree")
        yield Static(id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#tree", DirectoryTree).focus()
        self._show_dir(self._start)

    def _show_dir(self, path: Path) -> None:
        self.last_dir = path
        self.query_one("#path", Static).update(str(path))
        self.query_one("#status", Static).update(
            "↑/↓ — навигация, Enter — войти/выбрать, h — домой, b — ~/Books, l — последняя папка, Esc — назад"
        )

    def _goto(self, path: Path) -> None:
        if not path.is_dir():
            path = Path.home()
        tree = self.query_one("#tree", DirectoryTree)
        tree.path = path
        self._show_dir(path)

    @on(DirectoryTree.DirectorySelected)
    def _on_directory(self, event: DirectoryTree.DirectorySelected) -> None:
        self._show_dir(event.path)

    @on(DirectoryTree.FileSelected)
    def _on_file(self, event: DirectoryTree.FileSelected) -> None:
        self.dismiss(event.path)

    def action_close(self) -> None:
        self.dismiss(None)

    def action_go_home(self) -> None:
        self._goto(Path.home())

    def action_go_books(self) -> None:
        books = Path.home() / "Books"
        books.mkdir(parents=True, exist_ok=True)
        self._goto(books)

    def action_go_last(self) -> None:
        if self.last_dir is not None:
            self._goto(self.last_dir)
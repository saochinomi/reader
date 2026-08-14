from __future__ import annotations

from pathlib import Path

from textual.app import App

from ..db import LibraryDB
from ..models import ParsedBook
from .library_screen import LibraryScreen
from .reader_screen import ReaderScreen

CSS = """
$background: #0a0a0a;
$surface: #0a0a0a;
$panel: #101010;
$text: #c8c8c8;
$text-muted: #5c5c5c;
$primary: #7fbf7f;
$secondary: #1e1e1e;
$accent: #9ece6a;
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
    color: #7fbf7f;
    padding: 1 2 0 2;
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

DataTable {
    background: #0a0a0a;
    color: $text;
    padding: 0 1;
}

DataTable > .datatable--header {
    background: #0d0d0d;
    color: $text-muted;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #1f3a24;
    color: #9ece6a;
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
    background: #1f3a24;
    color: #9ece6a;
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
    background: #1f3a24;
    color: #9ece6a;
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

    def __init__(self, db_path: Path, open_path: Path | None = None):
        super().__init__()
        self.db_path = db_path
        self.db = LibraryDB(db_path)
        self.open_path = open_path
        self._books_cache: dict[int, ParsedBook] = {}

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

    def get_book(self, book_id: int) -> ParsedBook:
        if book_id not in self._books_cache:
            row = self.db.get_book(book_id)
            if row is None:
                raise KeyError(f"Книга {book_id} не найдена в БД")
            from ..importers import parse

            self._books_cache[book_id] = parse(Path(row["path"]))
        return self._books_cache[book_id]
from __future__ import annotations

import json
from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Input, Static

from ..db import LibraryDB
from .banner import banner
from .color_screen import ColorScreen
from .confirm_screen import ConfirmScreen
from .file_picker_screen import FilePickerScreen
from .help_screen import HelpScreen
from .key_bar import KeyBar
from .reader_screen import ReaderScreen
from .status_bar import StatusBar
from .tab_bar import TabBar


class LibraryScreen(Screen):
    BINDINGS = [
        Binding("i", "add_book", "Добавить"),
        Binding("tab", "next_tab", "Вкладки"),
        Binding("/", "focus_search", "Поиск"),
        Binding("u", "rescan", "Сканировать"),
        Binding("d", "delete_book", "Удалить"),
        Binding("r", "reimport", "Перечитать"),
        Binding("s", "cycle_sort", "Сортировка"),
        Binding("c", "choose_color", "Цвет"),
        Binding("?", "show_help", "Помощь"),
        Binding("q", "quit_app", "Выход"),
    ]

    SORT_KEYS = [("title", "названию"), ("author", "автору"), ("year", "году")]

    def __init__(self, db: LibraryDB, import_dir: str | None = None):
        super().__init__()
        self.db = db
        self.sort_key = "title"
        self.import_dir_on_start = import_dir
        self._rows: dict[str, dict] = {}
        self._selected_id: int | None = None
        self._pending_delete_id: int | None = None
        self._tabs: list[tuple[int, str]] = []

    def compose(self) -> ComposeResult:
        yield Static(banner(), id="banner")
        yield TabBar(on_open=self._open_from_tab, on_add=self.action_add_book)
        yield DataTable(id="books")
        yield Input(placeholder="Поиск по названию, автору, описанию…", id="search")
        yield StatusBar(id="statusbar")
        yield KeyBar(id="keybar")

    def on_mount(self) -> None:
        table = self.query_one("#books", DataTable)
        table.cursor_type = "row"
        table.zebra_stripes = True
        table.add_columns("Название", "Автор", "Год", "Формат", "Прогресс")
        self._refresh_table()
        self._update_tabs()
        self.query_one("#keybar", KeyBar).set_keys(KeyBar.library())
        if self.import_dir_on_start:
            self._import_dir(self.import_dir_on_start)
        else:
            self._scan_books_dir()

    def on_screen_resume(self, event) -> None:
        self._refresh_table()
        self._update_tabs()
        self.query_one("#keybar", KeyBar).set_keys(KeyBar.library())

    def _sorted(self, query: str = "") -> list:
        rows = self.db.search_books(query) if query else self.db.all_books()
        key = self.sort_key
        if key == "author":
            rows = sorted(rows, key=lambda r: (r["authors"], r["title"].lower()))
        elif key == "year":
            rows = sorted(rows, key=lambda r: (r["year"] is None, r["year"] or 0), reverse=True)
        else:
            rows = sorted(rows, key=lambda r: r["title"].lower())
        return rows

    def _refresh_table(self) -> None:
        table = self.query_one("#books", DataTable)
        table.clear()
        self._rows.clear()
        selected = self._selected_id
        selected_row = 0
        for i, row in enumerate(self._sorted(self.query_one("#search", Input).value)):
            key = str(row["id"])
            self._rows[key] = row
            table.add_row(
                row["title"],
                ", ".join(json.loads(row["authors"])),
                row["year"] or "—",
                row["format"].upper(),
                self._progress_text(row),
                key=key,
            )
            if selected == row["id"]:
                selected_row = i
        if self._rows:
            table.move_cursor(row=selected_row)
        query = self.query_one("#search", Input).value.strip()
        sort_label = dict(self.SORT_KEYS)[self.sort_key]
        self.query_one("#statusbar", StatusBar).browse(
            len(self._rows), sort_label=sort_label, query=query
        )

    @staticmethod
    def _progress_text(row) -> str:
        chapters = json.loads(row["chapters"])
        total = sum(c["n"] for c in chapters)
        if not total:
            return "—"
        done = sum(c["n"] for c in chapters[: row["chapter"] or 0]) + (row["paragraph"] or 0)
        pct = round(done * 100 / total)
        return f"{pct}%"

    def _selected_row(self) -> dict | None:
        table = self.query_one("#books", DataTable)
        cursor = table.cursor_coordinate
        if cursor is None:
            return None
        row_key = table.coordinate_to_cell_key(cursor).row_key
        return self._rows.get(row_key.value)

    def _current_book_id(self) -> int | None:
        row = self._selected_row()
        return int(row["id"]) if row else None

    # --- действия ---

    def action_add_book(self) -> None:
        self.app.push_screen(FilePickerScreen(), self._on_file_picked)

    def _on_file_picked(self, path: Path | None) -> None:
        if path is None:
            return
        if path.is_dir():
            self._import_dir(str(path))
            return
        self._import_and_open(path)

    def _import_and_open(self, path: Path) -> None:
        try:
            from ..importers import parse
            from ..library import add_parsed_book

            book = parse(path)
            book_id = add_parsed_book(self.db, path, book)
            self.app._books_cache[book_id] = book
        except Exception as e:  # noqa: BLE001
            self.app.notify(f"Не удалось открыть «{path.name}»: {e}", severity="error")
            return
        self._refresh_table()
        self._selected_id = book_id
        self._update_tabs(active=book_id)
        self.app.push_screen(ReaderScreen(self.db, book_id))

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_cycle_sort(self) -> None:
        keys = [k for k, _ in self.SORT_KEYS]
        self.sort_key = keys[(keys.index(self.sort_key) + 1) % len(keys)]
        self._refresh_table()

    def action_rescan(self) -> None:
        self._scan_books_dir()

    async def action_open_book(self) -> None:
        book_id = self._current_book_id()
        if book_id is None:
            self.app.notify("Нет выбранной книги", severity="warning")
            return
        self._selected_id = book_id
        try:
            self.app.get_book(book_id)
        except Exception as e:  # noqa: BLE001
            self.app.notify(f"Не удалось открыть: {e}", severity="error")
            return
        self._update_tabs(active=book_id)
        await self.app.push_screen(ReaderScreen(self.db, book_id))

    async def action_delete_book(self) -> None:
        book_id = self._current_book_id()
        if book_id is None:
            return
        row = self.db.get_book(book_id)
        self._pending_delete_id = book_id
        self.app.push_screen(
            ConfirmScreen(f"Удалить «{row['title']}» из библиотеки?"),
            self._on_delete_confirmed,
        )

    def _on_delete_confirmed(self, confirmed: bool) -> None:
        book_id = self._pending_delete_id
        if not confirmed or book_id is None:
            return
        self.db.remove_book(book_id)
        self.app._books_cache.pop(book_id, None)
        self._refresh_table()

    async def action_reimport(self) -> None:
        book_id = self._current_book_id()
        if book_id is None:
            return
        row = self.db.get_book(book_id)
        try:
            from ..library import import_book

            self.app._books_cache.pop(book_id, None)
            import_book(self.db, Path(row["path"]), force=True)
            self.app.notify("Книга перечитана")
        except Exception as e:  # noqa: BLE001
            self.app.notify(f"Ошибка: {e}", severity="error")
        self._refresh_table()

    def action_quit_app(self) -> None:
        self.app.exit()

    # --- вкладки ---

    def _recent_tabs(self) -> list[tuple[int, str]]:
        recent = self.db.recent_books(6)
        return [(int(r["id"]), r["title"]) for r in recent]

    def _update_tabs(self, active: int | None = None) -> None:
        self._tabs = self._recent_tabs()
        self.query_one(TabBar).refresh_tabs(self._tabs, active)

    def _open_from_tab(self, book_id: int) -> None:
        self._selected_id = book_id
        self.run_worker(self.action_open_book())

    def action_next_tab(self) -> None:
        if not self._tabs:
            return
        try:
            idx = [t for t in self._tabs if t[0] == self._current_book_id()]
            current = self._tabs.index(idx[0]) if idx else -1
        except (ValueError, IndexError):
            current = -1
        book_id = self._tabs[(current + 1) % len(self._tabs)][0]
        self._selected_id = book_id
        self.action_open_book()

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_choose_color(self) -> None:
        self.app.push_screen(ColorScreen())

    # --- события ---

    @on(Input.Changed, "#search")
    def _on_search_changed(self, event: Input.Changed) -> None:
        self._selected_id = None
        self._refresh_table()

    @on(DataTable.RowSelected, "#books")
    async def _on_row_selected(self, event: DataTable.RowSelected) -> None:
        row = self._rows.get(event.row_key.value)
        if row:
            self._selected_id = int(row["id"])
        await self.action_open_book()

    # --- сканирование ~/Books ---

    @work(thread=True)
    def _scan_books_dir(self) -> None:
        books = Path.home() / "Books"
        if not books.is_dir():
            return
        from ..library import import_directory

        db = LibraryDB(self.app.db_path)
        try:
            results = import_directory(db, books)
        finally:
            db.close()
        self.app.call_from_thread(self._scan_finished, results)

    def _scan_finished(self, results) -> None:
        if results:
            self._refresh_table()
            self._update_tabs()

    @work(thread=True)
    def _import_dir(self, directory: str) -> None:
        from ..library import import_directory

        db = LibraryDB(self.app.db_path)
        try:
            results = import_directory(db, Path(directory))
        finally:
            db.close()
        self.app.call_from_thread(self._import_finished, directory, results)

    def _import_finished(self, directory: str, results) -> None:
        ok = sum(1 for _, s in results if s)
        failed = [(p, e) for p, e in results if not e]
        self._refresh_table()
        self._update_tabs()
        if not failed:
            self.app.notify(f"Импортировано книг: {ok} из {directory}", severity="information")
        else:
            self.app.notify(
                f"Импортировано: {ok}, ошибок: {len(failed)} (пример: {failed[0][1]})",
                severity="warning",
            )
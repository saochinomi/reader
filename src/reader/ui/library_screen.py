from __future__ import annotations

import json
import time
from pathlib import Path

from textual import on, work
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Input, Static

from ..db import LibraryDB
from .all_bookmarks_screen import AllBookmarksScreen
from .color_screen import ColorScreen
from .confirm_screen import ConfirmScreen
from .file_picker_screen import FilePickerScreen
from .help_screen import HelpScreen
from .notes_screen import NotesScreen
from .reader_screen import ReaderScreen
from .shelf_screen import ShelfScreen
from .status_bar import StatusBar
from .tab_bar import TabBar
from .timer_screen import TimerScreen


class LibraryScreen(Screen):
    BINDINGS = [
        Binding("i", "add_book", "Добавить"),
        Binding("enter", "open_book", "Открыть"),
        Binding("tab", "tab_next", "Дальше"),
        Binding("shift+tab", "cursor_left", "Назад"),
        Binding("/", "focus_search", "Поиск"),
        Binding("u", "rescan", "Сканировать"),
        Binding("d", "delete_book", "Удалить"),
        Binding("B", "show_all_bookmarks", "Закладки"),
        Binding("H", "show_notes", "Заметки"),
        Binding("r", "reimport", "Перечитать"),
        Binding("s", "cycle_sort", "Сортировка"),
        Binding("c", "choose_color", "Цвет"),
        Binding("t", "show_timer", "Таймер"),
        Binding("S", "show_shelves", "Полки"),
        Binding("p", "put_on_shelf", "На полку"),
        Binding("g", "open_last_book", "Последняя"),
        Binding("j", "cursor_down", "Вниз"),
        Binding("k", "cursor_up", "Вверх"),
        Binding("down", "cursor_down", "Вниз"),
        Binding("up", "cursor_up", "Вверх"),
        Binding("left", "cursor_left", "Влево"),
        Binding("right", "cursor_right", "Вправо"),
        Binding("h", "focus_shelves", "Полки"),
        Binding("l", "focus_grid", "Карточки"),
        Binding("?", "show_help", "Помощь"),
        Binding("q", "quit_app", "Выход"),
    ]

    SORT_KEYS = [("title", "названию"), ("author", "автору"), ("year", "году")]
    CARD_W = 22
    SIDEBAR_W = 20
    WATCH_INTERVAL = 3.0

    def __init__(self, db: LibraryDB):
        super().__init__()
        self.db = db
        self.sort_key = "title"
        self._rows: dict[str, dict] = {}
        self._visible: list[int] = []
        self._selected_id: int | None = None
        self._pending_delete_id: int | None = None
        self._tabs: list[tuple[int, str]] = []
        self._current_shelf_id: int | None = None
        self._current_shelf_name: str = ""
        self._importing: set[str] = set()
        self._scanning = False
        self._last_cols = 0
        self._focus = "grid"
        self._shelves: list[tuple[int | None, str, int]] = []
        self._shelf_index = 0
        self._dropdown_open = False
        self._open_shelf_id: int | None = None
        self._open_books: list[dict] = []
        self._known_files: set[str] = set()
        self._failed: dict[str, float] = {}

    def compose(self) -> ComposeResult:
        with Horizontal(id="main_row"):
            with Vertical(id="sidebar"):
                yield Static("▦ ПОЛКИ", id="shelves_title")
                with VerticalScroll(id="shelf_scroll"):
                    yield Static(id="shelves")
            with Vertical(id="main_column"):
                yield Static(id="headline")
                yield Static(classes="divider")
                yield TabBar(on_open=self._open_from_tab, on_add=self.action_add_book)
                yield Static(classes="divider")
                with VerticalScroll(id="cards_scroll"):
                    yield Static(id="cards")
                yield Static(classes="divider")
                with Horizontal(id="search_row"):
                    yield Input(placeholder="Поиск по названию, автору, описанию…", id="search")
        yield StatusBar(id="statusbar")

    def on_mount(self) -> None:
        self._books_prefix = str(Path.home() / "Books") + "/"
        self._known_files = {
            r["path"] for r in self.db.all_books()
            if r["path"].startswith(self._books_prefix)
        }
        self._refresh_shelves()
        self._refresh_cards()
        self._update_tabs()
        self.set_interval(1.0, self._timer_tick)
        self.set_interval(self.WATCH_INTERVAL, self._watch_books_dir)
        self._watch_books_dir()
        self._scanning = True
        self._scan_books_dir()

    def on_resize(self) -> None:
        if self._cols() != self._last_cols:
            self._refresh_cards()

    def on_screen_resume(self, event) -> None:
        if self._current_shelf_id is not None:
            shelf = next(
                (r for r in self.db.all_shelves() if r["id"] == self._current_shelf_id), None
            )
            if shelf is None:
                self._current_shelf_id = None
                self._current_shelf_name = ""
        if self._dropdown_open and self._open_shelf_id is not None:
            shelf = next(
                (r for r in self.db.all_shelves() if r["id"] == self._open_shelf_id), None
            )
            if shelf is None:
                self._dropdown_open = False
        self._refresh_shelves()
        self._refresh_cards()
        self._update_tabs()

    def _cols(self) -> int:
        avail = max(20, self.size.width - self.SIDEBAR_W - 4)
        return max(1, avail // (self.CARD_W + 1))

    def _grid_width(self) -> int:
        return max(20, self.size.width - self.SIDEBAR_W - 4)

    def _sorted(self, query: str = "") -> list:
        if self._current_shelf_id is not None:
            rows = self.db.shelf_books(self._current_shelf_id)
            if query:
                like = query.casefold()
                rows = [
                    r
                    for r in rows
                    if like in r["title"].casefold()
                    or like in (r["authors"] or "").casefold()
                    or like in r["description"].casefold()
                ]
        else:
            rows = self.db.search_books(query) if query else self.db.all_books()
        key = self.sort_key
        if key == "author":
            rows = sorted(rows, key=lambda r: (r["authors"], r["title"].lower()))
        elif key == "year":
            rows = sorted(rows, key=lambda r: (r["year"] is None, r["year"] or 0), reverse=True)
        else:
            rows = sorted(rows, key=lambda r: r["title"].lower())
        return rows

    def _refresh_cards(self) -> None:
        rows = self._sorted(self.query_one("#search", Input).value)
        self._rows = {str(r["id"]): r for r in rows}
        self._visible = [int(r["id"]) for r in rows]
        if self._selected_id is not None and self._selected_id not in self._visible:
            self._selected_id = None
        if self._visible and self._selected_id is None:
            self._selected_id = self._visible[0]
        self._last_cols = self._cols()
        self._draw_cards()
        self._refresh_headline()
        self._refresh_status()

    def _draw_cards(self) -> None:
        cards = self.query_one("#cards", Static)
        if not self._visible:
            text = "нет книг - нажми i"
            cards.update(f"[#5c5c5c]{text.center(self._grid_width())}[/]")
            return
        summary = self.db.bookmarks_summary()
        last_id = self._last_read_id()
        cols = self._cols()
        width = self._grid_width()
        out = []
        for i in range(0, len(self._visible), cols):
            ids = self._visible[i : i + cols]
            frames = [
                self._card_lines(
                    self._rows[str(bid)],
                    bid == self._selected_id,
                    summary.get(bid, (0, ""))[0],
                    bid == last_id,
                )
                for bid in ids
            ]
            row_w = len(frames) * (self.CARD_W + 1) - 1
            pad = max(0, (width - row_w) // 2)
            for r in range(6):
                out.append(" " * pad + " ".join(fr[r] for fr in frames))
        cards.update("\n".join(out))
        row = self._visible.index(self._selected_id) // cols
        self.query_one("#cards_scroll", VerticalScroll).scroll_to(
            y=row * 7, animate=False
        )

    def _card_lines(
        self, row: dict, selected: bool, bookmarks: int, is_last: bool
    ) -> list[str]:
        accent, bright, bg, _dim = self.app.accent_colors()
        border = accent if selected else "#1c1c1c"
        inner = "#101010" if selected else "#0d0d0d"
        w = self.CARD_W - 2
        title = row["title"].strip()
        raw_authors = row["authors"] or ""
        if raw_authors.startswith("["):
            try:
                raw_authors = ", ".join(json.loads(raw_authors))
            except ValueError:
                pass
        authors = raw_authors.strip()
        c1 = title[:10].upper().center(w)
        c2 = (title[10:20].upper() if len(title) > 10 else "").center(w)
        t_line = title if len(title) <= w else title[: w - 1] + "…"
        chapters = json.loads(row["chapters"])
        total = sum(c["n"] for c in chapters)
        if total:
            done = sum(c["n"] for c in chapters[: row["chapter"] or 0]) + (row["paragraph"] or 0)
            pct = f"{round(done * 100 / total)}%"
        else:
            pct = "-"
        flag = f"[{bright}]◆[/] " if bookmarks else ""
        badge = f"[{bright}] ▷[/]" if is_last else ""
        right_len = (2 if bookmarks else 0) + len(pct) + (2 if is_last else 0)
        a_max = w - right_len - 1
        a_line = authors if len(authors) <= a_max else authors[: a_max - 1] + "…"
        a_line = a_line.ljust(w - right_len)
        return [
            f"[{border}]╭{'─' * w}╮[/]",
            f"[{border}]│[/][on {bg}][{bright}]{c1}[/][/][{border}]│[/]",
            f"[{border}]│[/][on {bg}][{accent}]{c2}[/][/][{border}]│[/]",
            f"[{border}]│[/][on {inner}][bold][#c8c8c8]{t_line.ljust(w)}[/][/][/][{border}]│[/]",
            f"[{border}]│[/][on {inner}][#8a8a8a]{a_line}[/][/]{flag}[{accent}]{pct}[/]{badge}[{border}]│[/]",
            f"[{border}]╰{'─' * w}╯[/]",
        ]

    def _shelf_rows(self) -> list[dict]:
        rows = [
            {"kind": "shelf", "sid": sid, "name": name, "n": n}
            for sid, name, n in self._shelves
        ]
        if self._dropdown_open:
            rows += [
                {"kind": "book", "id": int(r["id"]), "title": r["title"]}
                for r in self._open_books
            ]
        return rows

    def _refresh_shelves(self) -> None:
        accent, bright, bg, _dim = self.app.accent_colors()
        shelves = self.db.all_shelves()
        total = len(self.db.all_books())
        self._shelves = [(None, "Все книги", total)] + [
            (int(s["id"]), s["name"], s["n"]) for s in shelves
        ]
        if self._dropdown_open:
            self._open_books = self._sorted()
        rows = self._shelf_rows()
        if self._shelf_index >= len(rows):
            self._shelf_index = max(0, len(rows) - 1)
        current = self._current_shelf_id
        lines = []
        for i, entry in enumerate(rows):
            if entry["kind"] == "book":
                title = entry["title"]
                if len(title) > 16:
                    title = title[:15] + "…"
                text = f"  {title}"
            else:
                mark = "▸" if entry["sid"] == current else " "
                label = entry["name"]
                if len(label) > 13:
                    label = label[:12] + "…"
                text = f"{mark} {label:<11}{entry['n']:>4}"
            if self._focus == "shelves" and i == self._shelf_index:
                lines.append(f"[{bright} on {bg}]{text}[/]")
            elif entry["kind"] == "shelf" and entry["sid"] == current:
                lines.append(f"[{accent}]{text}[/]")
            else:
                lines.append(f"[#8a8a8a]{text}[/]")
        self.query_one("#shelves", Static).update("\n".join(lines))
        self.call_after_refresh(self._scroll_shelf_cursor)

    def _scroll_shelf_cursor(self) -> None:
        self.query_one("#shelf_scroll", VerticalScroll).scroll_to(
            y=self._shelf_index, animate=False
        )

    def _refresh_headline(self) -> None:
        accent, bright, _bg, _dim = self.app.accent_colors()
        parts = [f"[{bright}]READER[/]"]
        if self._current_shelf_name:
            parts.append(f"[#8a8a8a]полка: {self._current_shelf_name}[/]")
        parts.append(f"[#8a8a8a]книг: {len(self._visible)}[/]")
        query = self.query_one("#search", Input).value.strip()
        if query:
            parts.append(f"[#8a8a8a]«{query}»[/]")
        parts.append(f"[#5c5c5c]по {dict(self.SORT_KEYS)[self.sort_key]}[/]")
        self.query_one("#headline", Static).update("  ·  ".join(parts))

    def _last_read_id(self) -> int | None:
        recent = self.db.recent_books(1)
        return int(recent[0]["id"]) if recent else None

    def _timer_tick(self) -> None:
        self.app.timer_tick()
        self._refresh_status()

    def _refresh_status(self) -> None:
        query = self.query_one("#search", Input).value.strip()
        sort_label = dict(self.SORT_KEYS)[self.sort_key]
        self.query_one("#statusbar", StatusBar).browse(
            len(self._rows),
            sort_label=sort_label,
            query=query,
            timer=self.app.timer_text(),
            shelf=self._current_shelf_name,
        )

    def _selected_row(self) -> dict | None:
        if self._selected_id is None:
            return None
        return self._rows.get(str(self._selected_id))

    def _current_book_id(self) -> int | None:
        row = self._selected_row()
        return int(row["id"]) if row else None

    def _move_cursor(self, delta: int) -> None:
        if self._focus == "shelves":
            rows = self._shelf_rows()
            if not rows:
                return
            self._shelf_index = (self._shelf_index + delta) % len(rows)
            self._refresh_shelves()
            return
        if not self._visible:
            return
        if self._selected_id not in self._visible:
            self._selected_id = self._visible[0]
        idx = self._visible.index(self._selected_id)
        self._selected_id = self._visible[(idx + delta) % len(self._visible)]
        self._refresh_cards()

    def action_cursor_down(self) -> None:
        self._move_cursor(self._cols() if self._focus == "grid" else 1)

    def action_cursor_up(self) -> None:
        self._move_cursor(-(self._cols() if self._focus == "grid" else 1))

    def action_cursor_left(self) -> None:
        self._move_cursor(-1)

    def action_cursor_right(self) -> None:
        self._move_cursor(1)

    def action_focus_shelves(self) -> None:
        self._focus = "shelves"
        self._refresh_shelves()

    def action_focus_grid(self) -> None:
        self._focus = "grid"
        self._refresh_shelves()

    async def action_open_shelf(self) -> None:
        rows = self._shelf_rows()
        if not rows:
            return
        entry = rows[self._shelf_index]
        if entry["kind"] == "book":
            await self._open_book(entry["id"])
            return
        sid = entry["sid"]
        if self._dropdown_open and self._open_shelf_id == sid:
            self._dropdown_open = False
            self._shelf_index = next(
                i for i, (s, _n, _c) in enumerate(self._shelves) if s == sid
            )
            self._refresh_shelves()
            return
        self._dropdown_open = True
        self._open_shelf_id = sid
        self._current_shelf_id = sid
        self._current_shelf_name = entry["name"] if sid is not None else ""
        self._selected_id = None
        self._refresh_cards()
        self._open_books = self._sorted()
        self._shelf_index = len(self._shelves)
        self._refresh_shelves()

    def action_tab_next(self) -> None:
        if self._focus == "shelves":
            self._focus = "grid"
            self._refresh_shelves()
        self.action_cursor_right()


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
        self._refresh_cards()
        self._selected_id = book_id
        self._update_tabs(active=book_id)
        self.app.push_screen(ReaderScreen(self.db, book_id))

    def action_focus_search(self) -> None:
        self.query_one("#search", Input).focus()

    def action_cycle_sort(self) -> None:
        keys = [k for k, _ in self.SORT_KEYS]
        self.sort_key = keys[(keys.index(self.sort_key) + 1) % len(keys)]
        self._refresh_cards()

    def action_rescan(self) -> None:
        self._scan_books_dir()

    async def action_open_book(self) -> None:
        if self._focus == "shelves":
            await self.action_open_shelf()
            return
        book_id = self._current_book_id()
        if book_id is None:
            self.app.notify("Нет выбранной книги", severity="warning")
            return
        await self._open_book(book_id)

    async def _open_book(self, book_id: int) -> None:
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
        if self._current_shelf_id is not None:
            self.db.remove_book_from_shelf(self._current_shelf_id, book_id)
            self.app.notify(f"Снято с полки «{self._current_shelf_name}»", severity="information")
            self._refresh_cards()
            return
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
        self._refresh_cards()

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
        self._refresh_cards()

    def action_quit_app(self) -> None:
        self.app.exit()


    def _recent_tabs(self) -> list[tuple[int, str]]:
        recent = self.db.recent_books(6)
        return [(int(r["id"]), r["title"]) for r in recent]

    def _update_tabs(self, active: int | None = None) -> None:
        self._tabs = self._recent_tabs()
        self.query_one(TabBar).refresh_tabs(self._tabs, active)

    def _open_from_tab(self, book_id: int) -> None:
        self._selected_id = book_id
        self.run_worker(self.action_open_book())

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_choose_color(self) -> None:
        self.app.push_screen(ColorScreen())

    def action_show_timer(self) -> None:
        self.app.push_screen(TimerScreen())

    def action_show_shelves(self) -> None:
        self.app.push_screen(ShelfScreen(pick=False), self._on_shelf_picked)

    def _on_shelf_picked(self, shelf_id: int | None) -> None:
        if shelf_id is None:
            return
        if shelf_id == 0:
            self._current_shelf_id = None
            self._current_shelf_name = ""
        else:
            self._current_shelf_id = shelf_id
            shelf = next(
                (r for r in self.db.all_shelves() if r["id"] == shelf_id), None
            )
            self._current_shelf_name = shelf["name"] if shelf else ""
            if self._current_shelf_name:
                self.app.notify(f"Полка «{self._current_shelf_name}»", severity="information")
        for i, (sid, _n, _c) in enumerate(self._shelves):
            if sid == self._current_shelf_id:
                self._shelf_index = i
        self._focus = "grid"
        self._dropdown_open = False
        self._refresh_cards()
        self._refresh_shelves()

    def action_put_on_shelf(self) -> None:
        book_id = self._current_book_id()
        if book_id is None:
            return
        self.app.push_screen(ShelfScreen(pick=True), lambda shelf_id: self._on_put_on_shelf(book_id, shelf_id))

    def _on_put_on_shelf(self, book_id: int, shelf_id: int | None) -> None:
        if shelf_id is None or shelf_id == 0:
            return
        shelf = next((r for r in self.db.all_shelves() if r["id"] == shelf_id), None)
        name = shelf["name"] if shelf else ""
        if self.db.add_book_to_shelf(shelf_id, book_id):
            self.app.notify(f"Книга на полке «{name}»", severity="information")
        else:
            self.app.notify(f"Книга уже на полке «{name}»", severity="warning")

    def action_show_all_bookmarks(self) -> None:
        self.app.push_screen(AllBookmarksScreen(), self._on_all_bookmark)

    def action_show_notes(self) -> None:
        self.app.push_screen(NotesScreen(), self._on_note_selected)

    def _on_note_selected(self, result: tuple[int, int, int, int] | None) -> None:
        if result is None:
            return
        book_id, chapter, paragraph, offset = result
        self._selected_id = book_id
        try:
            self.app.get_book(book_id)
        except Exception as e:  # noqa: BLE001
            self.app.notify(f"Не удалось открыть книгу: {e}", severity="error")
            return
        self._update_tabs(active=book_id)
        self.app.push_screen(
            ReaderScreen(self.db, book_id, jump_to=(chapter, paragraph, offset))
        )

    def action_open_last_book(self) -> None:
        recent = self.db.recent_books(1)
        if not recent:
            self.app.notify("Нет недавних книг", severity="warning")
            return
        book_id = int(recent[0]["id"])
        self._selected_id = book_id
        try:
            self.app.get_book(book_id)
        except Exception as e:  # noqa: BLE001
            self.app.notify(f"Не удалось открыть: {e}", severity="error")
            return
        self._update_tabs(active=book_id)
        progress = self.db.get_progress(book_id)
        jump_to = (
            (progress["chapter"], progress["paragraph"]) if progress else None
        )
        self.app.push_screen(ReaderScreen(self.db, book_id, jump_to=jump_to))

    def _on_all_bookmark(self, result: tuple[int, int, int] | None) -> None:
        if result is None:
            return
        book_id, chapter, paragraph = result
        self._selected_id = book_id
        try:
            self.app.get_book(book_id)
        except Exception as e:  # noqa: BLE001
            self.app.notify(f"Не удалось открыть книгу: {e}", severity="error")
            return
        self._update_tabs(active=book_id)
        self.app.push_screen(ReaderScreen(self.db, book_id, jump_to=(chapter, paragraph)))


    @on(Input.Changed, "#search")
    def _on_search_changed(self, event: Input.Changed) -> None:
        if event.value == "?":
            self.query_one("#search", Input).value = ""
            self.action_show_help()
            return
        self._selected_id = None
        self._refresh_cards()

    @on(events.Click, "#cards")
    async def _on_cards_clicked(self, event: events.Click) -> None:
        if not self._visible:
            return
        cols = self._cols()
        start = event.offset.y // 7 * cols
        n = min(cols, len(self._visible) - start)
        if n <= 0:
            return
        row_w = n * (self.CARD_W + 1) - 1
        pad = max(0, (self._grid_width() - row_w) // 2)
        x = event.offset.x - pad
        if x < 0:
            return
        col = x // (self.CARD_W + 1)
        if col >= n:
            return
        self._selected_id = self._visible[start + col]
        self._focus = "grid"
        await self.action_open_book()

    @on(events.Click, "#shelves")
    async def _on_shelves_clicked(self, event: events.Click) -> None:
        rows = self._shelf_rows()
        if not rows:
            return
        row = event.offset.y
        if 0 <= row < len(rows):
            self._shelf_index = row
            self._focus = "shelves"
            await self.action_open_shelf()


    def _watch_books_dir(self) -> None:
        """Подхватывает новые книги в ~/Books и убирает книги пропавших файлов."""
        from ..importers.detect import sniff
        from ..models import Format

        books = Path.home() / "Books"
        if not books.is_dir():
            return
        now = time.time()
        found: set[str] = set()
        pending = []
        try:
            for path in books.rglob("*"):
                if not path.is_file():
                    continue
                if sniff(path) == Format.UNKNOWN:
                    continue
                key = str(path)
                found.add(key)
                if key in self._known_files:
                    continue
                if key in self._importing:
                    continue
                if self._failed.get(key, 0) > now - 30:
                    continue
                pending.append(key)
        except OSError as e:  # noqa: BLE001
            self.app.notify(f"Не удалось прочитать ~/Books: {e}", severity="error")
            return
        deleted = 0
        known = {
            r["path"] for r in self.db.all_books()
            if r["path"].startswith(self._books_prefix)
        }
        for key in known - found:
            if Path(key).exists():
                continue
            row = self.db.find_by_path(Path(key))
            self._known_files.discard(key)
            if row is None:
                continue
            self.app._books_cache.pop(row["id"], None)
            self.db.remove_book(row["id"])
            deleted += 1
        if deleted:
            self._refresh_cards()
            self._refresh_shelves()
            self._update_tabs()
            self.app.notify(f"Удалено книг: {deleted}", severity="warning")
        if pending and not self._scanning and len(self._importing) < 2:
            self._importing.update(pending)
            self.app.notify(f"Импортирую книг: {len(pending)}", severity="information")
            self._watch_import(pending)

    @work(thread=True)
    def _watch_import(self, paths: list[str]) -> None:
        from ..library import import_book

        db = LibraryDB(self.app.db_path)
        ok: list[str] = []
        fresh: list[str] = []
        try:
            for key in paths:
                path = Path(key)
                try:
                    if time.time() - path.stat().st_mtime < 1:
                        fresh.append(key)
                        continue
                    import_book(db, path)
                    ok.append(key)
                except Exception:
                    pass
        finally:
            db.close()
        self.app.call_from_thread(self._watch_import_finished, ok, fresh, paths)

    def _watch_import_finished(self, ok: list[str], fresh: list[str], paths: list[str]) -> None:
        self._known_files.update(ok)
        now = time.time()
        for key in set(paths) - set(ok) - set(fresh):
            self._failed[key] = now
        self._importing.difference_update(paths)
        if ok:
            self._refresh_cards()
            self._update_tabs()
            self.app.notify(f"Добавлено книг: {len(ok)}", severity="information")

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
        self._scanning = False
        if results:
            self._refresh_cards()
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
        self._refresh_cards()
        self._update_tabs()
        if not failed:
            self.app.notify(f"Импортировано книг: {ok} из {directory}", severity="information")
        else:
            self.app.notify(
                f"Импортировано: {ok}, ошибок: {len(failed)} (пример: {failed[0][1]})",
                severity="warning",
            )
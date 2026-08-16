from __future__ import annotations

import time
from bisect import bisect_left, bisect_right

from rich.markup import escape
from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Static

from ..db import LibraryDB
from ..models import ParsedBook
from ..renderer import BookRenderer
from .bookmarks_screen import BookmarksScreen
from .color_screen import ColorScreen
from .help_screen import HelpScreen
from .highlight_color_screen import HighlightColorScreen
from .highlight_colors import ACTION_COPY, HIGHLIGHT_COLORS, PREVIEW_BG
from .key_bar import KeyBar
from .notes_screen import NotesScreen
from .status_bar import StatusBar
from .timer_screen import TimerScreen

_WIDTH_MODES = (1.0, 0.8, 0.65)
_MAX_TEXT_WIDTH = 84


class ReaderScreen(Screen):
    BINDINGS = [
        Binding("j,down,space", "next_page", "След. стр."),
        Binding("k,up,backspace", "prev_page", "Пред. стр."),
        Binding("n", "next_chapter", "След. глава"),
        Binding("p", "prev_chapter", "Пред. глава"),
        Binding("[", "prev_bookmark", "Пред. закл."),
        Binding("]", "next_bookmark", "След. закл."),
        Binding("s", "add_bookmark", "Закладка"),
        Binding("H", "show_notes", "Заметки"),
        Binding("b", "show_bookmarks", "Закладки"),
        Binding("f", "cycle_width", "Ширина"),
        Binding("c", "choose_color", "Цвет"),
        Binding("t", "show_timer", "Таймер"),
        Binding("?", "show_help", "Помощь"),
        Binding("escape,q", "back", "Назад"),
    ]

    def __init__(self, db: LibraryDB, book_id: int, jump_to: tuple[int, int] | tuple[int, int, int] | None = None):
        super().__init__()
        self.db = db
        self.book_id = book_id
        self.jump_to = jump_to
        self.book: ParsedBook | None = None
        self.renderer: BookRenderer | None = None
        self.page_index = 0
        self.width_mode = 0
        self._highlight_until = 0.0
        self._sel_start: tuple[int, int, int] | None = None
        self._sel_end: tuple[int, int, int] | None = None
        self._sel_end_y: int | None = None
        self._sel_start_ly: int | None = None
        self._sel_text = ""
        self._mouse_sel = False

    def compose(self) -> ComposeResult:
        with Horizontal(id="main_row"):
            yield KeyBar(id="keybar")
            with Vertical(id="main_column"):
                yield Static(id="chapter")
                with Horizontal(id="content_row"):
                    yield Static(id="content")
        yield StatusBar(id="statusbar")

    def on_mount(self) -> None:
        self.query_one("#keybar", KeyBar).set_keys(KeyBar.reader())
        self.book = self.app.get_book(self.book_id)
        self.set_interval(1.0, self._timer_tick)
        self._rebuild_renderer()
        resumed = self.jump_to is not None
        if self.jump_to is not None:
            if len(self.jump_to) == 3:
                self.page_index = self.renderer.locate_offset(*self.jump_to)
            else:
                self.page_index = self.renderer.locate(*self.jump_to)
        else:
            row = self.db.get_progress(self.book_id)
            if row is not None:
                resumed = True
                self.page_index = self.renderer.locate(row["chapter"], row["paragraph"])
        self._draw()
        if resumed:
            self._highlight_until = time.monotonic() + 1.5
            self.set_timer(1.5, self._clear_highlight)
        page = self.renderer.render(self.page_index)
        self._mlog(
            f"start size={self.size} rw={self.renderer.width} rh={self.renderer.height} "
            f"reg={self.query_one('#content', Static).region} "
            f"meta={len(page.meta)} lines={len(page.lines)}"
        )

    def _clear_highlight(self) -> None:
        self._highlight_until = 0.0
        self._draw()

    def _mlog(self, line: str) -> None:
        with open("/tmp/reader_mouse.log", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S')} {line}\n")

    def _highlighted(self) -> bool:
        return time.monotonic() < self._highlight_until

    def _rebuild_renderer(self) -> None:
        assert self.book is not None
        keys_w = self.query_one("#keybar").size.width or KeyBar.WIDTH
        mode = _WIDTH_MODES[self.width_mode]
        width = max(20, int(min(_MAX_TEXT_WIDTH, self.size.width - keys_w - 2) * mode))
        height = max(5, self.size.height - 2)
        self.query_one("#content", Static).styles.width = width
        if self.renderer is None:
            self.renderer = BookRenderer(self.book, width=width, height=height)
            return
        current = self.renderer.render(self.page_index)
        self.renderer = BookRenderer(self.book, width=width, height=height)
        self.page_index = self.renderer.locate(current.chapter_index, current.paragraph_index)

    def _draw(self, highlight: bool | None = None) -> None:
        assert self.book is not None and self.renderer is not None
        page = self.renderer.render(self.page_index)
        _acc, bright, _bg, _dim = self.app.accent_colors()
        title = self.book.chapters[page.chapter_index].title or "…"
        self.query_one("#chapter", Static).update(f"[bold]{bright}- {title} -[/bold]")
        lines = page.lines if page.lines else ["…"]
        if lines and page.meta:
            lines = self._colorize(lines, page.meta)
        if (highlight if highlight is not None else self._highlighted()) and lines:
            lines = [f"[reverse]{escape(lines[0])}[/reverse]"] + lines[1:]
        self.query_one("#content", Static).update("\n".join(lines))
        self._refresh_status(page)
        self._save_progress(page.chapter_index, page.paragraph_index)

    def _colorize(self, lines: list[str], meta: list[tuple[int, int, int]]) -> list[str]:
        ranges: list[tuple[tuple, tuple, str]] = []
        for h in self.db.highlights(self.book_id):
            markup = HIGHLIGHT_COLORS.get(h["color"], PREVIEW_BG)
            ranges.append(
                (
                    (h["chapter_s"], h["paragraph_s"], h["offset_s"]),
                    (h["chapter_e"], h["paragraph_e"], h["offset_e"]),
                    markup,
                )
            )
        if self._sel_start is not None and self._sel_end is not None:
            s, e = sorted((self._sel_start, self._sel_end))
            if e > s:
                ranges.append((s, e, PREVIEW_BG))
        if not ranges:
            return [escape(line) for line in lines]
        out: list[str] = []
        for line, (mci, mpi, moff) in zip(lines, meta):
            out.append(self._paint(line, (mci, mpi, moff), ranges))
        return out

    @staticmethod
    def _paint(text: str, pos: tuple[int, int, int], ranges) -> str:
        end = pos[2] + len(text)
        for (cs, ps, os), (ce, pe, oe), markup in ranges:
            if (cs, ps, os) >= (pos[0], pos[1], end):
                continue
            if (ce, pe, oe) <= pos:
                continue
            start = max(os, pos[2])
            stop = min(oe, end)
            if stop <= start:
                continue
            ls, le = start - pos[2], stop - pos[2]
            return (
                f"{escape(text[:ls])}[{markup}]{escape(text[ls:le])}[/]"
                f"{escape(text[le:])}"
            )
        return escape(text)

    def _refresh_status(self, page=None) -> None:
        assert self.renderer is not None
        if page is None:
            page = self.renderer.render(self.page_index)
        total = self.renderer.page_count()
        pct = round((self.page_index + 1) * 100 / total) if total else 0
        self.query_one("#statusbar", StatusBar).read(
            self.book.title,
            chapter=f"гл. {page.chapter_index + 1}/{len(self.book.chapters)}",
            page=f"стр. {self.page_index + 1}/{total}",
            fmt=self.book.format.value.upper(),
            pct=pct,
            timer=self.app.timer_text(),
        )

    def _timer_tick(self) -> None:
        self.app.timer_tick()
        self._refresh_status()

    def _save_progress(self, chapter: int, paragraph: int) -> None:
        self.db.save_progress(self.book_id, chapter, paragraph, self.page_index)

    def on_resize(self) -> None:
        if self.renderer is not None:
            self._rebuild_renderer()
            self._draw()


    def action_next_page(self) -> None:
        if self.renderer and self.page_index < self.renderer.page_count() - 1:
            self.page_index += 1
            self._draw()

    def action_prev_page(self) -> None:
        if self.page_index > 0:
            self.page_index -= 1
            self._draw()

    def action_next_chapter(self) -> None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        if page.chapter_index < len(self.book.chapters) - 1:
            self.page_index = self.renderer.locate(page.chapter_index + 1, 0)
            self._draw()

    def action_prev_chapter(self) -> None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        if page.chapter_index > 0:
            self.page_index = self.renderer.locate(page.chapter_index - 1, 0)
            self._draw()

    def action_cycle_width(self) -> None:
        self.width_mode = (self.width_mode + 1) % len(_WIDTH_MODES)
        self._rebuild_renderer()
        self._draw()

    def action_add_bookmark(self) -> None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        note = (page.lines[0] if page.lines else "")[:60]
        self.db.add_bookmark(self.book_id, page.chapter_index, page.paragraph_index, note)
        self.app.notify("Закладка добавлена", severity="information")

    def _on_sel_action(
        self,
        result: str | None,
        start: tuple[int, int, int],
        end: tuple[int, int, int],
        text: str,
    ) -> None:
        self._sel_start = None
        self._sel_end = None
        self._sel_text = ""
        if result is None:
            self._draw()
            return
        if result == ACTION_COPY:
            self.app.copy_to_clipboard(text)
            self.app.notify("Текст скопирован", severity="information")
            self._draw()
            return
        self.db.add_highlight(self.book_id, *start, *end, result, text)
        self.app.notify(f"Заметка добавлена ({result})", severity="information")
        self._draw()

    def _mouse_pos(self, x: float, y: float) -> tuple[int, int, int] | None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        row = int(y)
        if not page.meta or row < 0 or row >= len(page.meta):
            return None
        ci, pi, off = page.meta[row]
        line = page.lines[row]
        col = max(0, min(int(x) - 1, len(line)))
        return ci, pi, off + col

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if event.button != 1:
            return
        region = self.query_one("#content", Static).region
        if not region.contains(event.screen_x, event.screen_y):
            return
        pos = self._mouse_pos(event.screen_x - region.x, event.screen_y - region.y)
        self._mlog(f"down b={event.button} sx={event.screen_x} sy={event.screen_y} reg={region} lx={event.screen_x - region.x} ly={event.screen_y - region.y} row={pos} start={pos}")
        if pos is None:
            return
        self._sel_start = pos
        self._sel_end = pos
        self._sel_end_y = int(event.screen_y - region.y)
        self._sel_start_ly = self._sel_end_y
        self._sel_text = ""
        self._mouse_sel = True

    def on_mouse_move(self, event: events.MouseMove) -> None:
        if not self._mouse_sel or event.button != 1:
            return
        region = self.query_one("#content", Static).region
        x = min(max(event.screen_x, region.x), region.right - 1)
        y = min(max(event.screen_y, region.y), region.bottom - 1)
        pos = self._mouse_pos(x - region.x, y - region.y)
        self._mlog(f"move b={event.button} sx={event.screen_x} sy={event.screen_y} reg={region} lx={event.screen_x - region.x} ly={event.screen_y - region.y} row={pos} end={self._sel_end}")
        if pos is not None and pos != self._sel_end:
            self._sel_end = pos
            self._sel_end_y = int(y - region.y)
            self._draw()

    def on_mouse_up(self, event: events.MouseUp) -> None:
        if event.button != 1 or not self._mouse_sel:
            return
        self._mouse_sel = False
        if self._sel_start is None or self._sel_end is None:
            return
        region = self.query_one("#content", Static).region
        up_pos = self._mouse_pos(event.screen_x - region.x, event.screen_y - region.y)
        self._mlog(f"up b={event.button} sx={event.screen_x} sy={event.screen_y} reg={region} lx={event.screen_x - region.x} ly={event.screen_y - region.y} row={up_pos} end_y={self._sel_end_y} end={self._sel_end}")
        if region.contains(event.screen_x, event.screen_y) and self._sel_end_y is not None:
            y = int(event.screen_y - region.y)
            if self._sel_start_ly is not None and y == self._sel_start_ly + 1 and self._sel_end_y <= self._sel_start_ly + 1:
                assert self.renderer is not None
                page = self.renderer.render(self.page_index)
                if self._sel_start_ly < len(page.meta):
                    ci, pi, off = page.meta[self._sel_start_ly]
                    self._sel_end = (ci, pi, off + len(page.lines[self._sel_start_ly]))
            elif abs(y - self._sel_end_y) <= 2:
                pos = self._mouse_pos(event.screen_x - region.x, event.screen_y - region.y)
                if pos is not None:
                    self._sel_end = pos
        start, end = sorted((self._sel_start, self._sel_end))
        if end <= start:
            self._sel_start = None
            self._sel_end = None
            self._draw()
            return
        self._sel_text = self._collect_text(start, end)
        self._draw()
        text = self._sel_text
        self.app.push_screen(
            HighlightColorScreen(),
            lambda result: self._on_sel_action(result, start, end, text),
        )

    def _collect_text(self, start: tuple[int, int, int], end: tuple[int, int, int]) -> str:
        assert self.book is not None
        parts: list[str] = []
        for ci, pi, t in self.book.paragraphs():
            if (ci, pi) < (start[0], start[1]) or (ci, pi) > (end[0], end[1]):
                continue
            s = start[2] if (ci, pi) == (start[0], start[1]) else 0
            e = end[2] if (ci, pi) == (end[0], end[1]) else len(t)
            if s < e:
                parts.append(t[s:e])
        text = " ".join(parts).strip()
        return text if len(text) <= 200 else text[:197] + "…"

    def action_show_notes(self) -> None:
        assert self.renderer is not None
        highlights = self.db.highlights(self.book_id)
        if not highlights:
            self.app.notify("Заметок нет (выделите текст мышью)", severity="information")
            return
        self.app.push_screen(
            NotesScreen(self.book_id), self._on_note_selected
        )

    def _on_note_selected(self, result: tuple[int, int, int, int] | None) -> None:
        if result is None:
            return
        assert self.renderer is not None
        book_id, chapter, paragraph, offset = result
        if book_id != self.book_id:
            return
        self.page_index = self.renderer.locate_offset(chapter, paragraph, offset)
        self._draw()

    def _jump_to_bookmark(self, pos: tuple[int, int], direction: int) -> None:
        assert self.renderer is not None
        marks = sorted(
            ((bm["id"], bm["chapter"], bm["paragraph"]) for bm in self.db.bookmarks(self.book_id)),
            key=lambda m: (m[1], m[2]),
        )
        if not marks:
            self.app.notify("Закладок нет (s - добавить)", severity="warning")
            return
        positions = [(m[1], m[2]) for m in marks]
        index = bisect_right(positions, pos) if direction > 0 else bisect_left(positions, pos) - 1
        if index < 0 or index >= len(marks):
            self.app.notify(
                "Дальше закладок нет" if direction > 0 else "Это первая закладка",
                severity="information",
            )
            return
        bookmark_id, chapter, paragraph = marks[index]
        self.page_index = self.renderer.locate(chapter, paragraph)
        self._draw()
        note = next(
            (bm["note"] or "…" for bm in self.db.bookmarks(self.book_id) if bm["id"] == bookmark_id),
            "…",
        )
        self.app.notify(f"Закладка: гл. {chapter + 1} - {note}")

    def action_next_bookmark(self) -> None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        self._jump_to_bookmark((page.chapter_index, page.paragraph_index), +1)

    def action_prev_bookmark(self) -> None:
        assert self.renderer is not None
        page = self.renderer.render(self.page_index)
        self._jump_to_bookmark((page.chapter_index, page.paragraph_index), -1)

    def action_show_bookmarks(self) -> None:
        assert self.renderer is not None
        bookmarks = self.db.bookmarks(self.book_id)
        if not bookmarks:
            self.app.notify("Закладок нет (s - добавить)", severity="information")
            return
        self.app.push_screen(
            BookmarksScreen(self.book_id, bookmarks, self._on_bookmark_deleted),
            self._on_bookmark_selected,
        )

    def _on_bookmark_selected(self, bookmark_id: int | None) -> None:
        if bookmark_id is None:
            return
        assert self.renderer is not None
        for bm in self.db.bookmarks(self.book_id):
            if bm["id"] == bookmark_id:
                self.page_index = self.renderer.locate(bm["chapter"], bm["paragraph"])
                self._draw()
                break

    def _on_bookmark_deleted(self, bookmark_id: int) -> None:
        pass

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_choose_color(self) -> None:
        self.app.push_screen(ColorScreen())

    def action_show_timer(self) -> None:
        self.app.push_screen(TimerScreen())

    def on_screen_resume(self, event) -> None:
        self.query_one("#keybar", KeyBar).set_keys(KeyBar.reader())
        if self.book is not None:
            self._draw()

    def action_back(self) -> None:
        if self._sel_start is not None:
            self._sel_start = None
            self._sel_end = None
            self._sel_text = ""
            self._draw()
            return
        self.app.pop_screen()
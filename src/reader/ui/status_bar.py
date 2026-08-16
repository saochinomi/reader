from __future__ import annotations

import time

from rich.cells import cell_len
from rich.text import Text
from textual.widgets import Static


class StatusBar(Static):
    """Центрированная строка режима: режим · контекст · прогресс."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: #0d0d0d;
        color: #8a8a8a;
        text-align: center;
        padding: 0 1;
    }
    """

    def browse(
        self,
        count: int,
        *,
        sort_label: str = "",
        query: str = "",
        timer: str = "",
        shelf: str = "",
    ) -> None:
        _acc, bright, _bg, _dim = self.app.accent_colors()
        left = f"[{bright}]BROWSE[/] [#c8c8c8]книг: {count}[/]"
        mid = []
        if shelf:
            mid.append(f"полка: {shelf}")
        if sort_label:
            mid.append(f"по {sort_label}")
        if query:
            mid.append(f"«{query}»")
        right = self._timer_zone(timer)
        self._zones(left, " · ".join(mid), right)

    def read(
        self,
        title: str,
        *,
        chapter: str = "",
        page: str = "",
        fmt: str = "",
        pct: int = 0,
        timer: str = "",
    ) -> None:
        _acc, bright, _bg, _dim = self.app.accent_colors()
        color = bright if pct >= 100 else _acc
        bar_len = 10
        filled = round(pct / 100 * bar_len)
        bar = "▰" * filled + "▱" * (bar_len - filled)
        left = f"[{bright}]READ[/] [#c8c8c8]{title}[/]"
        if chapter:
            left += f" [#8a8a8a]{chapter}[/]"
        mid = f"[{color}]{bar}[/] [#c8c8c8]{pct}%[/]"
        if page:
            mid += f" [#8a8a8a]{page}[/]"
        parts = [timer] if timer else []
        if fmt:
            parts.append(fmt)
        right = self._timer_zone(" · ".join(parts))
        self._zones(left, mid, right)

    def _timer_zone(self, timer: str) -> str:
        """Таймер, часы и когда закончится чтение."""
        parts = [timer] if timer else []
        parts.append(time.strftime("%H:%M"))
        if timer and not timer.startswith("‖"):
            mmss = timer.split(":")
            try:
                end = time.time() + int(mmss[0]) * 60 + int(mmss[1])
            except (ValueError, IndexError):
                end = None
            if end is not None:
                parts.append(f"→ {time.strftime('%H:%M', time.localtime(end))}")
        return f"[#8a8a8a]{' · '.join(parts)}[/]"

    def _zones(self, left: str, mid: str, right: str) -> None:
        width = max(1, self.size.width)
        lw = cell_len(Text.from_markup(left).plain)
        mw = cell_len(Text.from_markup(mid).plain)
        rw = cell_len(Text.from_markup(right).plain)
        free = width - lw - rw
        if free - mw < 0:
            mid_text = Text.from_markup(mid)
            mid_text.truncate(max(0, free), overflow="ellipsis")
            self.update(Text.from_markup(left) + " " + mid_text + " " + Text.from_markup(right))
            return
        pad_l = max(0, (free - mw) // 2)
        pad_r = max(0, free - mw - pad_l)
        self.update(f"{left}{' ' * pad_l}{mid}{' ' * pad_r}{right}")
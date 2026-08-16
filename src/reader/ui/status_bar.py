from __future__ import annotations

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

    @staticmethod
    def _mode(mode: str, bright: str) -> str:
        return f"[{bright}]{mode}[/]"

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
        parts = [self._mode("BROWSE", bright), f"[#c8c8c8]книг: {count}[/]"]
        if shelf:
            parts.append(f"[#8a8a8a]полка: {shelf}[/]")
        if sort_label:
            parts.append(f"[#8a8a8a]по {sort_label}[/]")
        if query:
            parts.append(f"[#8a8a8a]«{query}»[/]")
        if timer:
            parts.append(f"[#8a8a8a]{timer}[/]")
        self.update("  ·  ".join(parts))

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
        right = f"[#8a8a8a]{timer}[/]" if timer else ""
        if fmt:
            right += (f" [#8a8a8a]{fmt}[/]" if right else f"[#8a8a8a]{fmt}[/]")
        self._zones(left, mid, right)

    def _zones(self, left: str, mid: str, right: str) -> None:
        width = max(1, self.size.width)
        lw = len(Text.from_markup(left))
        mw = len(Text.from_markup(mid))
        rw = len(Text.from_markup(right))
        free = width - lw - rw
        pad_l = max(0, (free - mw) // 2)
        pad_r = max(0, free - mw - pad_l)
        self.update(f"{left}{' ' * pad_l}{mid}{' ' * pad_r}{right}")
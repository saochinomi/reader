from __future__ import annotations

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

    def browse(self, count: int, *, sort_label: str = "", query: str = "") -> None:
        _acc, bright, _bg, _dim = self.app.accent_colors()
        parts = [self._mode("BROWSE", bright), f"[#c8c8c8]книг: {count}[/]"]
        if sort_label:
            parts.append(f"[#8a8a8a]по {sort_label}[/]")
        if query:
            parts.append(f"[#8a8a8a]«{query}»[/]")
        self.update("  ·  ".join(parts))

    def read(
        self,
        title: str,
        *,
        chapter: str = "",
        page: str = "",
        fmt: str = "",
        pct: int = 0,
    ) -> None:
        _acc, bright, _bg, _dim = self.app.accent_colors()
        color = bright if pct >= 100 else _acc
        bar_len = 10
        filled = round(pct / 100 * bar_len)
        bar = "▰" * filled + "▱" * (bar_len - filled)
        parts = [self._mode("READ", bright), f"[#c8c8c8]{title}[/]"]
        if chapter:
            parts.append(f"[#8a8a8a]{chapter}[/]")
        if page:
            parts.append(f"[#8a8a8a]{page}[/]")
        if fmt:
            parts.append(f"[#8a8a8a]{fmt}[/]")
        parts.append(f"[{color}]{bar} {pct}%[/]")
        self.update("  ·  ".join(parts))
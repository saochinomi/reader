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
    def _mode(mode: str) -> str:
        return f"[#9ece6a]{mode}[/]"

    def browse(self, count: int, *, sort_label: str = "", query: str = "") -> None:
        parts = [self._mode("BROWSE"), f"[#c8c8c8]книг: {count}[/]"]
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
        color = "#9ece6a" if pct >= 100 else "#7fbf7f"
        bar_len = 10
        filled = round(pct / 100 * bar_len)
        bar = "▰" * filled + "▱" * (bar_len - filled)
        parts = [self._mode("READ"), f"[#c8c8c8]{title}[/]"]
        if chapter:
            parts.append(f"[#8a8a8a]{chapter}[/]")
        if page:
            parts.append(f"[#8a8a8a]{page}[/]")
        if fmt:
            parts.append(f"[#8a8a8a]{fmt}[/]")
        parts.append(f"[{color}]{bar} {pct}%[/]")
        self.update("  ·  ".join(parts))
from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    """Статус-бар в стиле lualine: разделы с фоном, режим, позиция, хоткеи."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: #0d0d0d;
        color: #9a9a9a;
    }
    """

    @staticmethod
    def _mode(mode: str, active: bool = False) -> str:
        color = "#1f3a24" if active else "#0d0d0d"
        text = "#9ece6a" if active else "#6a6a6a"
        return f"[{color}]{text} {mode} [/]"

    def browse(
        self,
        count: int,
        *,
        sort_label: str = "",
        query: str = "",
        keys: str = "i / s / u / d / ?",
    ) -> None:
        parts = [
            self._mode("BROWSE", active=True),
            f"[on #101010]#c8c8c8 книг: {count}[/]",
        ]
        if query:
            parts.append(f"[on #101010]#c8c8c8 «{query}»[/]")
        if sort_label:
            parts.append(f"[on #101010]#c8c8c8 по {sort_label}[/]")
        parts.append(f"[on #101010]#555555 {keys}[/]")
        self.update("".join(parts))

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
        parts = [
            self._mode("READ", active=True),
            f"[on #101010]#c8c8c8 {title}[/]",
        ]
        if chapter:
            parts.append(f"[on #101010]#8a8a8a {chapter}[/]")
        if page:
            parts.append(f"[on #101010]#8a8a8a {page}[/]")
        if fmt:
            parts.append(f"[on #101010]#8a8a8a {fmt}[/]")
        parts.append(f"[on #101010]{color} {bar} {pct}%[/]")
        self.update("".join(parts))
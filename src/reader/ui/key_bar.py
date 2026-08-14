from __future__ import annotations

from textual.widgets import Static

_SEP = "  "


class KeyBar(Static):
    """Панель горячих клавиш по центру: иконка + клавиша + подпись."""

    DEFAULT_CSS = """
    KeyBar {
        height: 1;
        background: #0d0d0d;
        text-align: center;
        padding: 0 1;
    }
    """

    @staticmethod
    def _seg(icon: str, key: str, label: str) -> str:
        return (
            f"[#7fbf7f]{icon}[/] [#9ece6a]{key}[/] "
            f"[#5c5c5c]{label}[/]"
        )

    def set_keys(self, items: list[tuple[str, str, str]]) -> None:
        """items: список (иконка, клавиша, подпись)."""
        self.update(_SEP.join(self._seg(*item) for item in items))

    @staticmethod
    def library() -> list[tuple[str, str, str]]:
        return [
            ("+", "i", "добавить"),
            ("⏎", "Enter", "открыть"),
            ("⌕", "/", "поиск"),
            ("⇅", "s", "сортировка"),
            ("⟳", "u", "скан"),
            ("✕", "d", "удалить"),
            ("⏭", "Tab", "вкладки"),
            ("?", "?", "помощь"),
        ]

    @staticmethod
    def reader() -> list[tuple[str, str, str]]:
        return [
            ("⏵", "j", "страница"),
            ("⏴", "k", "назад"),
            ("⏭", "n", "глава"),
            ("⏮", "p", "глава"),
            ("⚑", "s", "закладка"),
            ("☰", "b", "список"),
            ("⇔", "f", "ширина"),
            ("?", "?", "помощь"),
            ("⏴", "Esc", "назад"),
        ]
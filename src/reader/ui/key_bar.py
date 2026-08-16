from __future__ import annotations

from rich.markup import escape
from textual.widgets import Static

class KeyBar(Static):
    """Вертикальная панель клавиш слева: иконка + клавиша, без подписей."""

    WIDTH = 8

    DEFAULT_CSS = """
    KeyBar {
        height: 1fr;
        width: auto;
        background: #0a0a0a;
        color: #8a8a8a;
        padding: 1 1 1 2;
    }
    """

    def set_keys(self, items: list[tuple[str, str, str]]) -> None:
        """items: список (иконка, клавиша, подпись) - подписи не рисуются."""
        accent, bright, _bg, _dim = self.app.accent_colors()
        lines = [
            f"[{accent}]{escape(icon)}[/] [{bright}]{escape(key)}[/]"
            for icon, key, _label in items
        ]
        self.update("\n".join(lines))

    @staticmethod
    def library() -> list[tuple[str, str, str]]:
        return [
            ("+", "i", "добавить"),
            ("⏎", "↵", "открыть"),
            ("⏵", "g", "последняя"),
            ("⌕", "/", "поиск"),
            ("⇅", "s", "сортировка"),
            ("⟳", "u", "скан"),
            ("✕", "d", "удалить"),
            ("⚑", "B", "закладки"),
            ("🖍", "H", "заметки"),
            ("▤", "S", "полки"),
            ("▦", "p", "на полку"),
            ("⏭", "⇥", "вкладки"),
            ("◎", "c", "цвет"),
            ("⏳", "t", "таймер"),
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
            ("✎", "m", "выделить"),
            ("🖍", "H", "заметки"),
            ("«»", "[]", "закл."),
            ("☰", "b", "список"),
            ("⇔", "f", "ширина"),
            ("◎", "c", "цвет"),
            ("⏳", "t", "таймер"),
            ("?", "?", "помощь"),
            ("⏴", "⎋", "назад"),
        ]
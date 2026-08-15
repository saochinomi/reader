from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Static

_SECTIONS = [
    (
        "Библиотека",
        [
            ("i", "добавить книгу — файловый менеджер"),
            ("Enter", "открыть выбранную книгу"),
            ("/", "поиск"),
            ("s", "сортировка (название/автор/год)"),
            ("u", "пересканировать ~/Books"),
            ("r", "перечитать книгу из файла"),
            ("d", "удалить книгу (на полке — снять с полки)"),
            ("S", "полки — зайти на полку, создать, удалить"),
            ("p", "положить выбранную книгу на полку"),
            ("t", "таймер чтения (30 мин по умолчанию)"),
            ("q", "выход"),
        ],
    ),
    (
        "Вкладки (открытые книги)",
        [
            ("клик", "открыть книгу из вкладки"),
            ("+", "добавить книгу"),
        ],
    ),
    (
        "Читалка",
        [
            ("j / k", "следующая / предыдущая страница"),
            ("n / p", "следующая / предыдущая глава"),
            ("s", "закладка"),
            ("b", "список закладок (e — заметка к закладке)"),
            ("f", "ширина текста"),
            ("t", "таймер чтения (30 мин по умолчанию)"),
            ("Esc", "назад в библиотеку"),
        ],
    ),
]


class HelpScreen(Screen):
    BINDINGS = [
        Binding("escape,q", "dismiss", "Закрыть"),
    ]

    def compose(self) -> ComposeResult:
        yield Static(id="help")

    def on_mount(self) -> None:
        _acc, bright, _bg, _dim = self.app.accent_colors()
        lines = [f"[bold]{bright} Клавиши[/bold]", ""]
        for title, pairs in _SECTIONS:
            lines.append(f"[bold]#c8c8c8{title}[/bold]")
            for key, desc in pairs:
                lines.append(f"  [{_acc}]{key:>8}[/]  {desc}")
            lines.append("")
        lines.append("[#5c5c5c]Esc / q — закрыть[/]")
        self.query_one("#help", Static).update("\n".join(lines))

    def action_dismiss(self) -> None:
        self.app.pop_screen()
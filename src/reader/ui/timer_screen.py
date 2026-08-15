from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option


class TimerScreen(Screen):
    """Меню таймера чтения: старт/пауза, сброс, длительность."""

    BINDINGS = [
        Binding("escape,q", "dismiss", "Закрыть"),
    ]

    def compose(self) -> ComposeResult:
        yield Static("Таймер чтения", id="color_title")
        app = self.app
        options: list[Option] = []
        if app.timer_running():
            options.append(Option("⏸ Пауза", id="pause"))
        else:
            options.append(Option("▶ Запустить", id="start"))
        options.append(Option("⟳ Сбросить", id="reset"))
        options.append(Option("Длительность", id="label", disabled=True))
        for minutes in app.timer_choices():
            mark = "●" if minutes == app.timer_minutes() else "○"
            options.append(Option(f"{mark} {minutes} минут", id=f"m{minutes}"))
        yield OptionList(*options, id="timer")

    def on_mount(self) -> None:
        self.query_one("#timer", OptionList).focus()

    @on(OptionList.OptionSelected, "#timer")
    def _on_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id
        if option_id == "start" or option_id == "pause":
            self.app.timer_start_pause()
        elif option_id == "reset":
            self.app.timer_reset()
        elif option_id and option_id.startswith("m"):
            self.app.set_timer_minutes(int(option_id[1:]))
        self.app.pop_screen()

    def action_dismiss(self) -> None:
        self.app.pop_screen()
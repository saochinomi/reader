from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from .confirm_screen import ConfirmScreen


class ShelfScreen(Screen[int | None]):
    """Полки: выбор полки (Enter), новая (n), удалить (d)."""

    BINDINGS = [
        Binding("escape,q", "dismiss", "Закрыть"),
        Binding("n", "new_shelf", "Новая"),
        Binding("d", "delete_shelf", "Удалить"),
    ]

    def __init__(self, pick: bool = False):
        super().__init__()
        self.pick = pick

    def compose(self) -> ComposeResult:
        yield Static("Полки" if not self.pick else "Положить на полку", id="color_title")
        yield OptionList(id="shelves")
        yield Input(placeholder="Имя новой полки…", id="new_shelf")

    def _rebuild(self) -> None:
        ol = self.query_one("#shelves", OptionList)
        ol.clear_options()
        if not self.pick:
            ol.add_option(Option("▸ Все книги", id="all"))
        for row in self.app.db.all_shelves():
            ol.add_option(Option(f"{row['name']} - {row['n']}", id=f"s{row['id']}"))
        ol.add_option(Option("＋ Новая полка", id="new"))
        ol.focus()

    def on_mount(self) -> None:
        self._rebuild()

    def on_screen_resume(self, event) -> None:
        self._rebuild()

    @on(OptionList.OptionSelected, "#shelves")
    def _on_selected(self, event: OptionList.OptionSelected) -> None:
        option_id = event.option.id
        if option_id == "new":
            self.action_new_shelf()
        elif option_id == "all":
            self.dismiss(0)
        elif option_id and option_id.startswith("s"):
            self.dismiss(int(option_id[1:]))

    def action_new_shelf(self) -> None:
        inp = self.query_one("#new_shelf", Input)
        inp.focus()

    @on(Input.Submitted, "#new_shelf")
    def _on_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if name:
            self.app.db.create_shelf(name)
            self.app.notify(f"Полка «{name}» создана", severity="information")
            event.input.value = ""
        self._rebuild()

    def action_delete_shelf(self) -> None:
        ol = self.query_one("#shelves", OptionList)
        selected = ol.highlighted
        if selected is None:
            return
        option = ol.get_option_at_index(selected)
        if not option.id or not option.id.startswith("s"):
            return
        shelf_id = int(option.id[1:])
        shelf = next((r for r in self.app.db.all_shelves() if r["id"] == shelf_id), None)
        if shelf is None:
            return

        def confirm(ok: bool | None) -> None:
            if ok:
                self.app.db.delete_shelf(shelf_id)
                self.app.notify(f"Полка «{shelf['name']}» удалена", severity="information")
                self._rebuild()

        self.app.push_screen(ConfirmScreen(f"Удалить полку «{shelf['name']}»?"), confirm)

    def action_dismiss(self) -> None:
        self.dismiss(None)
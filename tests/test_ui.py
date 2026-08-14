from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, DirectoryTree, Static

from reader.ui.app import ReaderApp
from reader.ui.file_picker_screen import FilePickerScreen
from reader.ui.key_bar import KeyBar
from reader.ui.library_screen import LibraryScreen
from reader.ui.reader_screen import ReaderScreen
from reader.ui.status_bar import StatusBar
from reader.ui.tab_bar import TabBar

from fixtures import build_epub, build_fb2, build_txt, write_fixture


def _home(tmp_path: Path):
    """Перенаправляет ~ в tmp_path, чтобы тест не трогал реальный HOME."""
    import pathlib

    pathlib.Path.home = lambda: tmp_path


def _wait_nodes(pilot, tree: DirectoryTree) -> None:
    for _ in range(100):
        if tree.root.children:
            return
        asyncio.run_coroutine_threadsafe(pilot.pause(), asyncio.get_running_loop()).result()


async def _open_picker(app: ReaderApp, start: Path):
    app.push_screen(FilePickerScreen(start=start))


class TestUi:
    def test_pick_book_from_file_manager(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db")
            async with app.run_test(size=(100, 40)) as pilot:
                lib = app.screen
                assert isinstance(lib, LibraryScreen)
                assert lib._rows == {}

                # кнопка i — файловый менеджер
                await pilot.press("i")
                await pilot.pause()
                picker = app.screen
                assert isinstance(picker, FilePickerScreen)
                tree = picker.query_one(DirectoryTree)
                for _ in range(100):
                    await pilot.pause()
                    if tree.root.children:
                        break
                node = next(n for n in tree.root.children if n.data is not None and n.data.path == book)
                tree.select_node(node)
                for _ in range(50):
                    await pilot.pause()
                    if isinstance(app.screen, ReaderScreen):
                        break
                else:
                    raise AssertionError(f"не открылась читалка, экран: {type(app.screen).__name__}")
                reader = app.screen
                await pilot.press("j", "n", "s")
                await pilot.pause()
                assert len(app.db.bookmarks(reader.book_id)) == 1

                await pilot.press("escape")
                await pilot.pause()
                assert app.screen is lib
                assert len(lib._rows) == 1
                row = app.db.get_book(reader.book_id)
                assert row["title"] == "Тестовая книга"

        asyncio.run(scenario())

    def test_open_path_file_starts_reader(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.epub"
        write_fixture(book, build_epub())

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db", open_path=book)
            async with app.run_test(size=(100, 40)) as pilot:
                assert isinstance(app.screen, ReaderScreen)
                keybar = app.screen.query_one("#keybar", KeyBar)
                assert "закладка" in keybar.content and "ширина" in keybar.content
                await pilot.press("j")
                await pilot.pause()
                await pilot.press("escape")
                await pilot.pause()
                assert isinstance(app.screen, LibraryScreen)
                assert len(app.screen._rows) == 1

        asyncio.run(scenario())

    def test_banner_and_tabs_and_statusbar(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            from reader.library import import_book

            app = ReaderApp(tmp_path / "lib.db")
            async with app.run_test(size=(100, 40)) as pilot:
                lib = app.screen
                banner = lib.query_one("#banner", Static)
                assert "███████╗" in banner.content
                assert lib.query_one(TabBar) is not None
                status = lib.query_one(StatusBar)
                assert "книг: 0" in status.content

                book_id = import_book(app.db, book)
                app.db.save_progress(book_id, 0, 1, 1)
                lib._refresh_table()
                lib._update_tabs(active=book_id)
                await pilot.pause()
                assert len(status.content) > 0 and "книг: 1" in status.content
                tabs = lib.query_one(TabBar)
                for _ in range(50):
                    await pilot.pause()
                    if any(b.id and b.id.startswith("tab-") for b in tabs.query(Button)):
                        break
                assert any(b.id and b.id.startswith("tab-") for b in tabs.query(Button))

                keybar = lib.query_one("#keybar", KeyBar)
                assert "добавить" in keybar.content and "сортировка" in keybar.content
                status_center = "книг: 1" in status.content

        asyncio.run(scenario())

    def test_choose_accent_color(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db")
            async with app.run_test(size=(100, 40)) as pilot:
                lib = app.screen
                assert app.theme == "reader-green"

                await pilot.press("c")
                await pilot.pause()
                from reader.ui.color_screen import ColorScreen

                assert isinstance(app.screen, ColorScreen)
                await pilot.press("down", "enter")
                await pilot.pause()
                assert app._accent_name == "blue"
                assert app.theme == "reader-blue"
                assert isinstance(app.screen, LibraryScreen)
                keybar = lib.query_one("#keybar", KeyBar)
                for _ in range(50):
                    await pilot.pause()
                    if "#82aaff" in keybar.content:
                        break
                assert "#82aaff" in keybar.content

        asyncio.run(scenario())

    def test_search_cyrillic(self, tmp_path: Path):
        _home(tmp_path)
        b1 = tmp_path / "a.fb2"
        b2 = tmp_path / "b.epub"
        b3 = tmp_path / "c.txt"
        write_fixture(b1, build_fb2())
        write_fixture(b2, build_epub())
        write_fixture(b3, build_txt())

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db")
            async with app.run_test(size=(100, 40)) as pilot:
                from reader.library import import_book

                from reader.library import import_book

                import_book(app.db, b1)
                import_book(app.db, b2)
                import_book(app.db, b3)
                lib = app.screen
                lib._refresh_table()
                assert len(lib._rows) == 3
                lib.query_one("#search").value = "тес"
                await pilot.pause()
                assert len(lib._rows) == 2
                lib.query_one("#search").value = ""
                await pilot.pause()
                assert len(lib._rows) == 3

        asyncio.run(scenario())

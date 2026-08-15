from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from textual.widgets import Button, DataTable, DirectoryTree, Static

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
            app = ReaderApp(tmp_path / "lib.db", splash=False)
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
            app = ReaderApp(tmp_path / "lib.db", open_path=book, splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                assert isinstance(app.screen, ReaderScreen)
                keybar = app.screen.query_one("#keybar", KeyBar)
                assert "⚑" in keybar.content and "⇔" in keybar.content
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

            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                lib = app.screen
                banner = lib.query_one("#banner", Static)
                assert "███████╗" in banner.content
                assert "██████╔╝" in banner.content
                assert "╚═════╝" in banner.content
                lines = banner.content.split("\n")
                assert len(set(len(l) for l in lines)) == 1
                assert lines[0].rstrip() == "██████╗ ███████╗ █████╗ ██████╗ ███████╗██████╗"
                assert lines[2].rstrip() == "██████╔╝█████╗  ███████║██║  ██║█████╗  ██████╔╝"
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
                assert "+" in keybar.content and "⇅" in keybar.content
                status_center = "книг: 1" in status.content

        asyncio.run(scenario())

    def test_choose_accent_color(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db", splash=False)
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

    def test_parse_cache(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        from reader.cache import load_or_parse
        from reader.db import LibraryDB
        from reader.library import import_book
        from reader.models import file_hash

        db = LibraryDB(tmp_path / "lib.db")
        import_book(db, book)
        hash_ = file_hash(book)
        assert db.get_parsed_cache(hash_) is not None

        import reader.cache as cache_module

        def boom(path):
            raise AssertionError("кэш не должен парсить файл")

        orig = cache_module.parse
        cache_module.parse = boom
        try:
            parsed = load_or_parse(db, book)
            assert parsed.title == "Тестовая книга"
            db.clear_parsed_cache(hash_)
            with pytest.raises(AssertionError):
                load_or_parse(db, book)
        finally:
            cache_module.parse = orig
        db.close()

    def test_bookmark_jumps(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "big.txt"
        big = ("Абзац книги. Ещё предложение текста.\n\n" * 300).encode("utf-8")
        write_fixture(book, big)

        async def scenario():
            from reader.library import import_book

            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                book_id = import_book(app.db, book)
                app.push_screen(ReaderScreen(app.db, book_id))
                await pilot.pause()
                reader = app.screen
                await pilot.press("s")
                await pilot.pause()
                await pilot.press("j", "j", "j", "j", "j", "s")
                await pilot.pause()
                assert len(app.db.bookmarks(book_id)) == 2

                await pilot.press("[")
                await pilot.pause()
                assert reader.page_index < 3
                await pilot.press("]")
                await pilot.pause()
                assert reader.page_index >= 3

        asyncio.run(scenario())

    def test_all_bookmarks_global(self, tmp_path: Path):
        _home(tmp_path)
        b1 = tmp_path / "a.fb2"
        b2 = tmp_path / "b.epub"
        write_fixture(b1, build_fb2())
        write_fixture(b2, build_epub())

        async def scenario():
            from reader.library import import_book
            from reader.ui.all_bookmarks_screen import AllBookmarksScreen

            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                id1 = import_book(app.db, b1)
                id2 = import_book(app.db, b2)
                app.db.add_bookmark(id1, 0, 1, "заметка 1")
                app.db.add_bookmark(id2, 1, 2, "заметка 2")

                await pilot.press("B")
                await pilot.pause()
                screen = app.screen
                assert isinstance(screen, AllBookmarksScreen)
                ol = screen.query_one("#list")
                assert ol.option_count == 2
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, ReaderScreen)
                assert app.screen.book_id == id1

        asyncio.run(scenario())

    def test_centered_layout(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            from reader.library import import_book

            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                lib = app.screen
                table = lib.query_one("#books")
                keys_w = lib.query_one("#keybar").size.width
                assert keys_w > 0
                assert table.styles.width.value == 100 - keys_w - 2
                card = lib.query_one("#last_book")
                assert card.styles.width.value == 100 - keys_w - 2
                assert card.display
                assert card.parent.id == "last_row"
                assert card.styles.text_align == "center"
                assert "\n" in card.content  # type: ignore
                assert "Нет недавних книг" in card.content  # type: ignore
                tab_bar = lib.query_one(TabBar)
                children = list(lib.query("*"))
                assert children.index(card) < children.index(tab_bar)
                search = lib.query_one("#search")
                assert search.styles.width.value == 100 - keys_w - 2
                assert search.parent.id == "search_row"
                assert lib.query_one("#keybar").parent.id == "main_row"
                assert table.parent.id == "table_row"
                assert tab_bar.parent.id == "main_column"
                assert lib.query_one("#main_row").children[0].id == "keybar"

                book_id = import_book(app.db, book)
                app.db.save_progress(book_id, 0, 1, 1)
                lib._refresh_table()
                await pilot.pause()
                assert "Тестовая книга" in card.content  # type: ignore
                assert "прочитано" in card.content  # type: ignore

                app.push_screen(ReaderScreen(app.db, book_id))
                await pilot.pause()
                reader = app.screen
                content = reader.query_one("#content")
                assert content.styles.width.value <= 84
                assert reader.query_one("#content_row") is not None
                chapter = reader.query_one("#chapter")
                assert "───" in chapter.content

        asyncio.run(scenario())

    def test_narrow_window_last_book_visible(self, tmp_path: Path):
        _home(tmp_path)

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(80, 40)) as pilot:
                lib = app.screen
                card = lib.query_one("#last_book")
                assert card.display
                keys_w = lib.query_one("#keybar").size.width
                table = lib.query_one("#books")
                assert table.styles.width.value == 80 - keys_w - 2
                assert card.styles.width.value == 80 - keys_w - 2

        asyncio.run(scenario())

    def test_splash_screen(self, tmp_path: Path):
        _home(tmp_path)

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db", splash=True)
            async with app.run_test(size=(100, 40)) as pilot:
                from reader.ui.splash_screen import SplashScreen

                assert isinstance(app.screen, SplashScreen)
                logo = app.screen.query_one("#splash_logo")
                assert "██████╗" in logo.content  # type: ignore
                hint = app.screen.query_one("#splash_hint")
                assert "Enter" in hint.content  # type: ignore
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, LibraryScreen)

        asyncio.run(scenario())

    def test_vertical_keybar_layout(self, tmp_path: Path):
        _home(tmp_path)

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                lib = app.screen
                main_row = lib.query_one("#main_row")
                assert main_row.children[0].id == "keybar"
                keybar = lib.query_one("#keybar", KeyBar)
                assert "\n" in keybar.content  # type: ignore
                assert "↵" in keybar.content and "⎋" not in keybar.content  # type: ignore
                assert "закладка" not in keybar.content  # type: ignore

                book = tmp_path / "book.fb2"
                write_fixture(book, build_fb2())
                from reader.library import import_book

                app.push_screen(ReaderScreen(app.db, import_book(app.db, book)))
                await pilot.pause()
                reader = app.screen
                assert reader.query_one("#main_row").children[0].id == "keybar"
                assert "⎋" in reader.query_one("#keybar", KeyBar).content  # type: ignore

        asyncio.run(scenario())

    def test_bookmarks_column_in_library(self, tmp_path: Path):
        _home(tmp_path)
        b1 = tmp_path / "a.fb2"
        b2 = tmp_path / "b.epub"
        write_fixture(b1, build_fb2())
        write_fixture(b2, build_epub())

        async def scenario():
            from reader.library import import_book

            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                id1 = import_book(app.db, b1)
                import_book(app.db, b2)
                lib = app.screen
                lib._refresh_table()
                table = lib.query_one("#books", DataTable)
                assert table.get_row_at(0)[1] == ""
                app.db.add_bookmark(id1, 0, 1, "заметка")
                app.db.add_bookmark(id1, 1, 2, "")
                lib._refresh_table()
                assert table.get_row_at(0)[1] == "⚑ 2"

        asyncio.run(scenario())

    def test_highlight_resume_spot(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            from reader.library import import_book

            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                book_id = import_book(app.db, book)
                app.db.save_progress(book_id, 1, 1, 1)
                app.push_screen(ReaderScreen(app.db, book_id))
                await pilot.pause()
                reader = app.screen
                content = reader.query_one("#content")
                assert "[reverse]" in content.content  # type: ignore
                await pilot.pause(1.6)
                assert "[reverse]" not in content.content  # type: ignore

        asyncio.run(scenario())

    def test_no_highlight_for_new_book(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            from reader.library import import_book

            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                book_id = import_book(app.db, book)
                app.push_screen(ReaderScreen(app.db, book_id))
                await pilot.pause()
                reader = app.screen
                content = reader.query_one("#content")
                assert "[reverse]" not in content.content  # type: ignore

        asyncio.run(scenario())

    def test_open_last_book(self, tmp_path: Path):
        _home(tmp_path)
        b1 = tmp_path / "a.fb2"
        b2 = tmp_path / "b.epub"
        write_fixture(b1, build_fb2())
        write_fixture(b2, build_epub())

        async def scenario():
            from reader.library import import_book

            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                id1 = import_book(app.db, b1)
                id2 = import_book(app.db, b2)
                app.db.save_progress(id1, 0, 1, 1)
                app.db.save_progress(id2, 2, 3, 0)
                app.db._conn.execute("UPDATE books SET last_opened = ? WHERE id = ?", (1000, id1))
                app.db._conn.execute("UPDATE books SET last_opened = ? WHERE id = ?", (2000, id2))
                app.db._conn.commit()
                lib = app.screen
                lib._refresh_table()
                await pilot.pause()
                card = lib.query_one("#last_book")
                assert "b.epub" in card.content or "Тестовая" in card.content  # type: ignore
                await pilot.press("g")
                await pilot.pause()
                assert isinstance(app.screen, ReaderScreen)
                assert app.screen.book_id == id2
                assert app.screen.page_index >= 0

        asyncio.run(scenario())

    def test_reading_timer(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                lib = app.screen
                assert app.timer_minutes() == 30
                assert "⏳ 30:00" in lib.query_one("#statusbar", StatusBar).content
                assert "30:00" in app.timer_text()

                app.set_timer_minutes(45)
                assert app.timer_minutes() == 45
                assert "timer_minutes" in (tmp_path / ".config" / "reader" / "config.json").read_text(
                    encoding="utf-8"
                )

                await pilot.press("t")
                await pilot.pause()
                assert app.screen.__class__.__name__ == "TimerScreen"
                await pilot.press("escape")
                await pilot.pause()

                app.timer_start_pause()
                assert app.timer_running()
                app._timer_deadline = __import__("time").monotonic() - 5
                app.timer_tick()
                assert not app.timer_running()
                assert app.timer_left_seconds() == 0

                from reader.library import import_book

                app.push_screen(ReaderScreen(app.db, import_book(app.db, book)))
                await pilot.pause()
                status = app.screen.query_one("#statusbar", StatusBar)
                assert "⏳" in status.content or "⏸" in status.content

        asyncio.run(scenario())

    def test_shelves(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                lib = app.screen
                shelf_id = app.db.create_shelf("Мануалы")
                from reader.library import import_book

                book_id = import_book(app.db, book)

                await pilot.press("S")
                await pilot.pause()
                assert app.screen.__class__.__name__ == "ShelfScreen"
                await pilot.press("escape")
                await pilot.pause()

                app.db.add_book_to_shelf(shelf_id, book_id)
                app.push_screen(
                    __import__("reader.ui.shelf_screen", fromlist=["ShelfScreen"]).ShelfScreen(
                        pick=False
                    ),
                    lib._on_shelf_picked,
                )
                await pilot.pause()
                lib._on_shelf_picked(shelf_id)
                await pilot.pause()
                assert lib._current_shelf_id == shelf_id
                assert len(lib._rows) == 1
                assert "полка: Мануалы" in lib.query_one("#statusbar", StatusBar).content

                lib._on_shelf_picked(0)
                await pilot.pause()
                assert lib._current_shelf_id is None
                assert len(lib._rows) == 1

        asyncio.run(scenario())

    def test_bookmark_note_edit(self, tmp_path: Path):
        _home(tmp_path)
        book = tmp_path / "book.fb2"
        write_fixture(book, build_fb2())

        async def scenario():
            app = ReaderApp(tmp_path / "lib.db", splash=False)
            async with app.run_test(size=(100, 40)) as pilot:
                from reader.library import import_book

                book_id = import_book(app.db, book)
                app.db.add_bookmark(book_id, 0, 1, "старая заметка")
                app.push_screen(ReaderScreen(app.db, book_id))
                await pilot.pause()

                await pilot.press("b")
                await pilot.pause()
                assert app.screen.__class__.__name__ == "BookmarksScreen"
                await pilot.press("e")
                await pilot.pause()
                assert app.screen.__class__.__name__ == "EditNoteScreen"
                await pilot.press("ctrl+u")
                await pilot.press("с", "т", "р", ".", " ", "1", "1", "3", "6")
                await pilot.press("enter")
                await pilot.pause()
                assert app.db.bookmarks(book_id)[0]["note"] == "стр. 1136"

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
            app = ReaderApp(tmp_path / "lib.db", splash=False)
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

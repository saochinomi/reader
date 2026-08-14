from __future__ import annotations

from pathlib import Path

import pytest

from reader.db import LibraryDB
from reader.importers import parse
from reader.models import Format
from reader.renderer import BookRenderer

from fixtures import build_epub, build_fb2, build_txt, write_fixture


@pytest.fixture
def book_txt(tmp_path: Path) -> Path:
    p = tmp_path / "book.txt"
    write_fixture(p, build_txt())
    return p


@pytest.fixture
def book_fb2(tmp_path: Path) -> Path:
    p = tmp_path / "book.fb2"
    write_fixture(p, build_fb2())
    return p


@pytest.fixture
def book_epub(tmp_path: Path) -> Path:
    p = tmp_path / "book.epub"
    write_fixture(p, build_epub())
    return p


@pytest.fixture
def db(tmp_path: Path) -> LibraryDB:
    d = LibraryDB(tmp_path / "lib.db")
    yield d
    d.close()


class TestTxt:
    def test_format_and_title(self, book_txt: Path):
        book = parse(book_txt)
        assert book.format == Format.TXT
        assert book.title == "book"

    def test_chapters_split(self, book_txt: Path):
        book = parse(book_txt)
        titles = [c.title for c in book.chapters]
        assert titles == ["", "Вторая глава"]
        assert book.text_length > 0


class TestFb2:
    def test_metadata(self, book_fb2: Path):
        book = parse(book_fb2)
        assert book.format == Format.FB2
        assert book.title == "Тестовая книга"
        assert book.authors == ["Иван Автор"]
        assert book.year == 2020
        assert book.language == "ru"

    def test_chapters(self, book_fb2: Path):
        book = parse(book_fb2)
        assert [c.title for c in book.chapters] == ["Глава первая", "Подраздел", "Глава вторая"]
        assert len(book.chapters[0].paragraphs) == 2
        assert book.chapters[1].paragraphs == ["Абзац подраздела."]


class TestEpub:
    def test_metadata(self, book_epub: Path):
        book = parse(book_epub)
        assert book.format == Format.EPUB
        assert book.title == "Тестовая книга"
        assert "Иван Автор" in book.authors
        assert book.year == 2020
        assert book.language == "ru"

    def test_chapters_and_nav(self, book_epub: Path):
        book = parse(book_epub)
        assert len(book.chapters) == 2
        assert book.chapters[0].title == "Первая глава"
        assert book.chapters[1].title == "Вторая глава"
        assert len(book.chapters[0].paragraphs) == 2


class TestRenderer:
    def test_pagination_roundtrip(self, book_fb2: Path):
        book = parse(book_fb2)
        r = BookRenderer(book, width=40, height=10)
        assert r.page_count() >= 1
        first = r.render(0)
        assert first.lines
        last = r.render(r.page_count() - 1)
        assert last.lines

    def test_locate_last(self, book_fb2: Path):
        book = parse(book_fb2)
        r = BookRenderer(book, width=40, height=10)
        assert r.locate(99, 99) == r.page_count() - 1


class TestDb:
    def test_upsert_and_progress(self, db: LibraryDB, book_epub: Path):
        book = parse(book_epub)
        book_id = db.upsert_book(book_epub, book, "abc")
        assert db.get_book(book_id)["title"] == "Тестовая книга"
        db.save_progress(book_id, 1, 0, 5)
        row = db.all_books()[0]
        assert row["chapter"] == 1 and row["scroll"] == 5

    def test_bookmarks(self, db: LibraryDB, book_fb2: Path):
        book = parse(book_fb2)
        book_id = db.upsert_book(book_fb2, book, "abc")
        db.add_bookmark(book_id, 0, 1, "важное место")
        bms = db.bookmarks(book_id)
        assert len(bms) == 1
        db.remove_bookmark(bms[0]["id"])
        assert db.bookmarks(book_id) == []

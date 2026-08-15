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

    def test_marked_chapters(self, tmp_path: Path):
        p = tmp_path / "marked.txt"
        write_fixture(
            p,
            (
                "# 1. Предисловие\n\nТекст предисловия.\n\n"
                "## Глава 2: Пролог\n\nТекст пролога.\n\n"
                "Глава 3. #Начало\n\nТекст начала.\n"
            ).encode("utf-8"),
        )
        book = parse(p)
        assert [c.title for c in book.chapters] == ["Предисловие", "Пролог", "Начало"]


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


class TestHtml:
    def test_parse(self, tmp_path: Path):
        p = tmp_path / "book.html"
        write_fixture(
            p,
            (
                "<html><head><meta charset=\"utf-8\"><title>HTML-книга</title></head><body>"
                "<h1>Глава первая</h1><p>Текст первый.</p><p>Текст второй.</p>"
                "<h2># 2. Подглава</h2><p>Текст третий.</p>"
                "</body></html>"
            ).encode("utf-8"),
        )
        book = parse(p)
        assert book.format == Format.HTML
        assert book.title == "HTML-книга"
        assert [c.title for c in book.chapters] == ["Глава первая", "Подглава"]
        assert book.chapters[0].paragraphs == ["Текст первый.", "Текст второй."]


class TestMarkdown:
    def test_parse(self, tmp_path: Path):
        p = tmp_path / "book.md"
        write_fixture(
            p,
            (
                "# Глава 1\n\nТекст главы 1.\n\n"
                "## Глава 2\n\n- пункт один\n- пункт два\n\n1. нумерованный\n"
            ).encode("utf-8"),
        )
        book = parse(p)
        assert book.format == Format.MARKDOWN
        assert [c.title for c in book.chapters] == ["Глава 1", "Глава 2"]
        assert book.chapters[1].paragraphs == ["пункт один", "пункт два", "нумерованный"]


class TestRtf:
    def test_parse(self, tmp_path: Path):
        p = tmp_path / "book.rtf"

        def cp1251_hex(s: str) -> str:
            return "".join(f"\\'{b:02x}" for b in s.encode("cp1251"))

        write_fixture(
            p,
            (
                "{\\rtf1\\ansi\\ansicpg1251{\\fonttbl{\\f0 Arial;}}"
                "{\\info{\\title " + cp1251_hex("Моя RTF-книга") + "}}"
                + cp1251_hex("Глава 1")
                + "\\par "
                + cp1251_hex("Текст первой главы.")
                + "\\par "
                + cp1251_hex("Глава 2")
                + "\\par "
                + cp1251_hex("Текст второй главы.")
                + "}"
            ).encode("ascii"),
        )
        book = parse(p)
        assert book.format == Format.RTF
        assert book.title == "Моя RTF-книга"
        assert [c.title for c in book.chapters] == ["Глава 1", "Глава 2"]
        assert book.chapters[0].paragraphs == ["Текст первой главы."]


class TestDocx:
    def test_parse(self, tmp_path: Path):
        p = tmp_path / "book.docx"
        w = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        document = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<w:document xmlns:w="{w}"><w:body>'
            f'<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Глава 1</w:t></w:r></w:p>'
            f'<w:p><w:r><w:t>Текст главы.</w:t></w:r></w:p>'
            f"</w:body></w:document>"
        )
        core = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
            'xmlns:dc="http://purl.org/dc/elements/1.1/">'
            "<dc:title>DOCX-книга</dc:title><dc:creator>Иван Автор</dc:creator></cp:coreProperties>"
        )
        import io
        import zipfile

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("word/document.xml", document)
            zf.writestr("docProps/core.xml", core)
        write_fixture(p, buf.getvalue())
        book = parse(p)
        assert book.format == Format.DOCX
        assert book.title == "DOCX-книга"
        assert book.authors == ["Иван Автор"]
        assert [c.title for c in book.chapters] == ["Глава 1"]
        assert book.chapters[0].paragraphs == ["Текст главы."]


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
        db.update_bookmark_note(bms[0]["id"], "стр. 1136–1140 · Jcc")
        assert db.bookmarks(book_id)[0]["note"] == "стр. 1136–1140 · Jcc"
        assert db.bookmarks_summary() == {book_id: (1, "стр. 1136–1140 · Jcc")}
        db.remove_bookmark(bms[0]["id"])
        assert db.bookmarks(book_id) == []
        assert db.bookmarks_summary() == {}

    def test_shelves(self, db: LibraryDB, book_fb2: Path, book_epub: Path):
        book = parse(book_fb2)
        b1 = db.upsert_book(book_fb2, book, "abc")
        b2 = db.upsert_book(book_epub, parse(book_epub), "def")
        s1 = db.create_shelf("Техника")
        s2 = db.create_shelf("Художка")
        assert db.add_book_to_shelf(s1, b1)
        assert db.add_book_to_shelf(s1, b2)
        assert not db.add_book_to_shelf(s1, b1)
        assert [r["id"] for r in db.shelf_books(s1)] == [b1, b2]
        shelves = db.all_shelves()
        assert {r["name"]: r["n"] for r in shelves} == {"Техника": 2, "Художка": 0}
        db.remove_book_from_shelf(s1, b1)
        assert [r["id"] for r in db.shelf_books(s1)] == [b2]
        db.delete_shelf(s2)
        assert {r["name"] for r in db.all_shelves()} == {"Техника"}

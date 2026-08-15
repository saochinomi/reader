from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from .models import ParsedBook


class LibraryDB:
    """SQLite-хранилище: книги, закладки, прогресс чтения."""

    def __init__(self, path: Path | str):
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                hash TEXT NOT NULL,
                format TEXT NOT NULL,
                title TEXT NOT NULL,
                authors TEXT NOT NULL DEFAULT '[]',
                year INTEGER,
                language TEXT,
                description TEXT NOT NULL DEFAULT '',
                text_length INTEGER NOT NULL DEFAULT 0,
                chapters TEXT NOT NULL DEFAULT '[]',
                added_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_opened INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS progress (
                book_id INTEGER PRIMARY KEY REFERENCES books(id) ON DELETE CASCADE,
                chapter INTEGER NOT NULL DEFAULT 0,
                paragraph INTEGER NOT NULL DEFAULT 0,
                scroll INTEGER NOT NULL DEFAULT 0,
                updated_at INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS bookmarks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL REFERENCES books(id) ON DELETE CASCADE,
                chapter INTEGER NOT NULL,
                paragraph INTEGER NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at INTEGER NOT NULL DEFAULT (unixepoch())
            );
            CREATE TABLE IF NOT EXISTS parsed_cache (
                hash TEXT PRIMARY KEY,
                blob BLOB NOT NULL,
                saved_at INTEGER NOT NULL DEFAULT (unixepoch())
            );
            CREATE INDEX IF NOT EXISTS idx_bookmarks_book ON bookmarks(book_id);
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def upsert_book(self, path: Path, book: ParsedBook, hash_: str) -> int:
        cur = self._conn.execute(
            """
            INSERT INTO books (path, hash, format, title, authors, year, language,
                               description, text_length, chapters)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(path) DO UPDATE SET
                hash = excluded.hash,
                format = excluded.format,
                title = excluded.title,
                authors = excluded.authors,
                year = excluded.year,
                language = excluded.language,
                description = excluded.description,
                text_length = excluded.text_length,
                chapters = excluded.chapters
            """,
            (
                str(path),
                hash_,
                book.format.value,
                book.title,
                json.dumps(book.authors, ensure_ascii=False),
                book.year,
                book.language,
                book.description,
                book.text_length,
                json.dumps(
                    [{"title": c.title, "n": len(c.paragraphs)} for c in book.chapters],
                    ensure_ascii=False,
                ),
            ),
        )
        self._conn.commit()
        return cur.lastrowid

    def all_books(self) -> list[sqlite3.Row]:
        cur = self._conn.execute(
            """
            SELECT b.*, p.chapter, p.paragraph, p.scroll
            FROM books b LEFT JOIN progress p ON p.book_id = b.id
            ORDER BY b.title COLLATE NOCASE
            """
        )
        return cur.fetchall()

    def get_book(self, book_id: int) -> sqlite3.Row | None:
        cur = self._conn.execute("SELECT * FROM books WHERE id = ?", (book_id,))
        return cur.fetchone()

    def recent_books(self, limit: int = 6) -> list[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT * FROM books WHERE last_opened > 0 ORDER BY last_opened DESC LIMIT ?",
            (limit,),
        )
        return cur.fetchall()

    def get_progress(self, book_id: int) -> sqlite3.Row | None:
        cur = self._conn.execute(
            "SELECT chapter, paragraph, scroll FROM progress WHERE book_id = ?",
            (book_id,),
        )
        return cur.fetchone()

    def find_by_path(self, path: Path) -> sqlite3.Row | None:
        cur = self._conn.execute("SELECT * FROM books WHERE path = ?", (str(path),))
        return cur.fetchone()

    def remove_book(self, book_id: int) -> None:
        self._conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        self._conn.commit()

    def save_progress(self, book_id: int, chapter: int, paragraph: int, scroll: int) -> None:
        self._conn.execute(
            """
            INSERT INTO progress (book_id, chapter, paragraph, scroll, updated_at)
            VALUES (?, ?, ?, ?, unixepoch())
            ON CONFLICT(book_id) DO UPDATE SET
                chapter = excluded.chapter,
                paragraph = excluded.paragraph,
                scroll = excluded.scroll,
                updated_at = excluded.updated_at
            """,
            (book_id, chapter, paragraph, scroll),
        )
        self._conn.execute("UPDATE books SET last_opened = unixepoch() WHERE id = ?", (book_id,))
        self._conn.commit()

    def bookmarks(self, book_id: int) -> list[sqlite3.Row]:
        cur = self._conn.execute(
            "SELECT * FROM bookmarks WHERE book_id = ? ORDER BY chapter, paragraph",
            (book_id,),
        )
        return cur.fetchall()

    def add_bookmark(self, book_id: int, chapter: int, paragraph: int, note: str = "") -> None:
        self._conn.execute(
            "INSERT INTO bookmarks (book_id, chapter, paragraph, note) VALUES (?, ?, ?, ?)",
            (book_id, chapter, paragraph, note),
        )
        self._conn.commit()

    def remove_bookmark(self, bookmark_id: int) -> None:
        self._conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        self._conn.commit()

    def all_bookmarks(self) -> list[sqlite3.Row]:
        cur = self._conn.execute(
            """
            SELECT bm.*, b.title AS book_title
            FROM bookmarks bm JOIN books b ON b.id = bm.book_id
            ORDER BY bm.book_id, bm.chapter, bm.paragraph
            """
        )
        return cur.fetchall()

    # --- кэш разобранных книг ---

    def get_parsed_cache(self, hash_: str) -> bytes | None:
        cur = self._conn.execute(
            "SELECT blob FROM parsed_cache WHERE hash = ?", (hash_,)
        )
        row = cur.fetchone()
        return row["blob"] if row else None

    def put_parsed_cache(self, hash_: str, blob: bytes) -> None:
        self._conn.execute(
            """
            INSERT INTO parsed_cache (hash, blob) VALUES (?, ?)
            ON CONFLICT(hash) DO UPDATE SET blob = excluded.blob
            """,
            (hash_, blob),
        )
        self._conn.commit()

    def clear_parsed_cache(self, hash_: str) -> None:
        self._conn.execute("DELETE FROM parsed_cache WHERE hash = ?", (hash_,))
        self._conn.commit()

    def search_books(self, query: str) -> list[sqlite3.Row]:
        like = query.casefold()
        return [
            r
            for r in self.all_books()
            if like in r["title"].casefold()
            or like in (r["authors"] or "").casefold()
            or like in r["description"].casefold()
        ]

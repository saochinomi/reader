from __future__ import annotations

import pickle
from pathlib import Path

from .db import LibraryDB
from .models import ParsedBook, file_hash


def load_or_parse(db: LibraryDB, path: Path) -> ParsedBook:
    """Возвращает книгу из SQLite-кэша (по хэшу файла) или парсит заново."""
    hash_ = file_hash(path)
    blob = db.get_parsed_cache(hash_)
    if blob is not None:
        try:
            book = pickle.loads(blob)
        except Exception:  # noqa: BLE001 - повреждённый кэш пересоздаём
            book = None
        if isinstance(book, ParsedBook) and book.chapters:
            return book
    book = parse(path)
    db.put_parsed_cache(hash_, pickle.dumps(book))
    return book


def parse(path: Path) -> ParsedBook:
    from .importers import parse as _parse

    return _parse(path)
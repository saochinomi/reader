from __future__ import annotations

import pickle
from pathlib import Path

from .db import LibraryDB
from .importers import parse
from .models import ParsedBook, file_hash


def add_parsed_book(db: LibraryDB, path: Path, book: ParsedBook, force: bool = False) -> int:
    """Сохраняет уже распарсенную книгу в библиотеку. Возвращает id."""
    hash_ = file_hash(path)
    existing = db.find_by_path(path)
    if existing and existing["hash"] == hash_ and not force:
        return existing["id"]
    db.put_parsed_cache(hash_, pickle.dumps(book))
    return db.upsert_book(path, book, hash_)


def import_book(db: LibraryDB, path: Path, force: bool = False) -> int:
    """Парсит книгу и добавляет её в библиотеку. Возвращает id."""
    book = parse(path)
    return add_parsed_book(db, path, book, force=force)


def import_directory(db: LibraryDB, directory: Path, force: bool = False) -> list[tuple[str, bool]]:
    """Рекурсивно импортирует все книги из папки. (путь, успех)"""
    results: list[tuple[str, bool]] = []
    if not directory.is_dir():
        return results
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".txt", ".epub", ".fb2", ".zip", ".fb2.zip"):
            continue
        try:
            import_book(db, path, force=force)
            results.append((str(path), True))
        except Exception as e:  # noqa: BLE001 — одна плохая книга не должна рушить импорт
            results.append((f"{path}: {e}", False))
    return results

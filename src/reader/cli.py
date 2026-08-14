from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .db import LibraryDB
from .library import import_directory
from .ui.app import ReaderApp


def _default_db_path() -> Path:
    base = Path.home() / ".local" / "share" / "reader"
    return base / "library.db"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reader",
        description="Консольная читалка книг (TXT, EPUB, FB2). "
        "Без аргументов открывает библиотеку; можно передать файл книги или папку.",
    )
    parser.add_argument("path", nargs="?", type=Path, help="файл книги (.txt/.epub/.fb2) или папка")
    parser.add_argument("--library", type=Path, default=_default_db_path(), help="путь к файлу библиотеки SQLite")
    parser.add_argument(
        "--import", dest="import_dir", metavar="DIR",
        help="рекурсивно импортировать книги из папки и выйти",
    )
    args = parser.parse_args(argv)

    args.library.parent.mkdir(parents=True, exist_ok=True)
    db = LibraryDB(args.library)

    if args.import_dir:
        results = import_directory(db, Path(args.import_dir))
        ok = sum(1 for _, s in results if s)
        print(f"Импортировано: {ok}, ошибок: {len(results) - ok}")
        for path, success in results:
            print(("  OK  " if success else "  ERR ") + path)
        db.close()
        return 0

    if args.path is not None and not args.path.exists():
        print(f"reader: путь не существует: {args.path}", file=sys.stderr)
        return 2

    try:
        ReaderApp(args.library, open_path=args.path).run()
    except Exception as e:  # noqa: BLE001
        print(f"Ошибка запуска: {e}", file=sys.stderr)
        return 1
    finally:
        db.close()
    return 0

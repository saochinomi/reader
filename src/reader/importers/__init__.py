from __future__ import annotations

from pathlib import Path

from ..models import Format, ParsedBook
from .detect import sniff
from .epub import parse_epub
from .fb2 import parse_fb2
from .txt import parse_txt

PARSERS = {
    Format.EPUB: parse_epub,
    Format.FB2: parse_fb2,
    Format.TXT: parse_txt,
}


def parse(path: Path) -> ParsedBook:
    """Определяет формат файла и парсит его."""
    fmt = sniff(path)
    parser = PARSERS.get(fmt)
    if parser is None:
        raise ValueError(f"Неподдерживаемый формат: {path.suffix}")
    return parser(path)

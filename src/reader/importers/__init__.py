from __future__ import annotations

from pathlib import Path

from ..models import Format, ParsedBook
from .detect import sniff
from .docx import parse_docx
from .epub import parse_epub
from .fb2 import parse_fb2
from .html import parse_html
from .markdown import parse_markdown
from .rtf import parse_rtf
from .txt import parse_txt

PARSERS = {
    Format.EPUB: parse_epub,
    Format.FB2: parse_fb2,
    Format.TXT: parse_txt,
    Format.HTML: parse_html,
    Format.MARKDOWN: parse_markdown,
    Format.RTF: parse_rtf,
    Format.DOCX: parse_docx,
}


def parse(path: Path) -> ParsedBook:
    """Определяет формат файла и парсит его."""
    fmt = sniff(path)
    parser = PARSERS.get(fmt)
    if parser is None:
        raise ValueError(f"Неподдерживаемый формат: {path.suffix}")
    return parser(path)

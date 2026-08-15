from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..models import Format, ParsedBook
from .txt import _split_chapters


def parse_djvu(path: Path) -> ParsedBook:
    djvutxt = shutil.which("djvutxt")
    if djvutxt:
        result = subprocess.run(
            [djvutxt, str(path)],
            capture_output=True,
            check=False,
            timeout=120,
        )
        text = result.stdout.decode("utf-8", errors="replace")
        if text.strip():
            return ParsedBook(
                format=Format.DJVU,
                title=path.stem,
                chapters=_split_chapters(text),
            )
    try:
        import djvu.decode  # type: ignore

        doc = djvu.decode.Context().new_document(djvu.decode.FileURI(str(path)))
        doc.decode(verbose=False)
        pages = [page.text.decode("utf-8", errors="replace") for page in doc.pages]
        text = "\n".join(p for p in pages if p)
        if text.strip():
            return ParsedBook(
                format=Format.DJVU,
                title=path.stem,
                chapters=_split_chapters(text),
            )
    except ImportError:
        pass
    raise ValueError(
        "DJVU требует djvutxt (пакет djvulibre) или библиотеку python-djvu"
    )
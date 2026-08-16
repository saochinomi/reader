from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from ..models import Format, ParsedBook
from .txt import _split_chapters


def parse_doc(path: Path) -> ParsedBook:
    for tool in ("soffice", "libreoffice"):
        exe = shutil.which(tool)
        if not exe:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(
                [exe, "--headless", "--convert-to", "txt:Text", "--outdir", tmp, str(path)],
                capture_output=True,
                check=False,
                timeout=120,
            )
        if result.returncode == 0:
            txt = Path(tmp) / (path.stem + ".txt")
            if txt.exists():
                text = txt.read_text(encoding="utf-8", errors="replace")
                if text.strip():
                    return ParsedBook(
                        format=Format.DOC,
                        title=path.stem,
                        chapters=_split_chapters(text),
                    )
    if shutil.which("antiword"):
        result = subprocess.run(
            [shutil.which("antiword"), str(path)],
            capture_output=True,
            check=False,
            timeout=120,
        )
        text = result.stdout.decode("utf-8", errors="replace")
        if text.strip():
            return ParsedBook(
                format=Format.DOC,
                title=path.stem,
                chapters=_split_chapters(text),
            )
    raise ValueError(
        "DOC требует LibreOffice (soffice) или antiword - установите одно из них"
    )
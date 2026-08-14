from __future__ import annotations

from pathlib import Path

from ..models import Format

FB2_MAGIC = b"<?xml"
FB2_NS = b"<FictionBook"
FB2_NS2 = b"FictionBook"


def detect_format(path: Path) -> Format:
    ext = path.suffix.lower().lstrip(".")
    if ext == Format.EPUB.value:
        return Format.EPUB
    if ext == Format.FB2.value:
        return Format.FB2
    if ext == Format.TXT.value:
        return Format.TXT
    if ext in (".fb2.zip", ".zip"):
        if path.suffix.lower() == ".zip":
            import zipfile

            try:
                with zipfile.ZipFile(path) as zf:
                    if any(n.lower().endswith(".fb2") for n in zf.namelist()):
                        return Format.FB2
            except zipfile.BadZipFile:
                pass
    if ext == ".epub" or ext in (".txt", ".text"):
        return Format(ext)
    return Format.UNKNOWN


def sniff(path: Path) -> Format:
    """Определение по расширению + содержимому, включая FB2 без расширения."""
    fmt = detect_format(path)
    if fmt != Format.UNKNOWN:
        return fmt
    try:
        with open(path, "rb") as f:
            head = f.read(512)
    except OSError:
        return Format.UNKNOWN
    if head.lstrip().startswith(FB2_MAGIC) and FB2_NS in head or FB2_NS2 in head:
        return Format.FB2
    return Format.UNKNOWN

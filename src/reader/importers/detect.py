from __future__ import annotations

from pathlib import Path

from ..models import Format

FB2_MAGIC = b"<?xml"
FB2_NS = b"<FictionBook"
FB2_NS2 = b"FictionBook"


_EXT_FORMATS = {
    "epub": Format.EPUB,
    "fb2": Format.FB2,
    "txt": Format.TXT,
    "text": Format.TXT,
    "html": Format.HTML,
    "htm": Format.HTML,
    "md": Format.MARKDOWN,
    "markdown": Format.MARKDOWN,
    "rtf": Format.RTF,
    "docx": Format.DOCX,
    "pdf": Format.PDF,
    "mobi": Format.MOBI,
    "azw": Format.MOBI,
    "azw3": Format.MOBI,
    "djvu": Format.DJVU,
    "djv": Format.DJVU,
    "doc": Format.DOC,
}


def detect_format(path: Path) -> Format:
    ext = path.suffix.lower().lstrip(".")
    if ext == "zip":
        import zipfile

        try:
            with zipfile.ZipFile(path) as zf:
                if any(n.lower().endswith(".fb2") for n in zf.namelist()):
                    return Format.FB2
        except zipfile.BadZipFile:
            pass
    return _EXT_FORMATS.get(ext, Format.UNKNOWN)


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

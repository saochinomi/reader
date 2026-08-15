from __future__ import annotations

import struct
from pathlib import Path

from ..models import Format, ParsedBook
from .html import parse_html_text

_ENCODINGS = {
    1252: "cp1252",
    1251: "cp1251",
    65001: "utf-8",
    20127: "ascii",
}


def _decode_palmdoc(data: bytes) -> bytes:
    out = bytearray()
    pos = 0
    n = len(data)
    while pos < n:
        c = data[pos]
        pos += 1
        if c == 0x00:
            break
        if c <= 0x08:
            out += data[pos : pos + c]
            pos += c
        elif c == 0x09:
            if pos >= n:
                break
            b = data[pos]
            pos += 1
            if b == 0:
                out += b"\x00"
            elif b == 1:
                out += out[:32]
            elif b == 2:
                out += b"\xa0"
            else:
                out += b"\x00" * b
        elif c == 0x0A:
            out += b" "
        elif c == 0x0B:
            out += b" " * 32
        elif c == 0x0C:
            out += b"\t"
        elif c == 0x0D:
            out += b"\r\n"
        elif c <= 0x1F:
            if pos >= n:
                break
            b = data[pos]
            pos += 1
            length = ((c >> 2) & 0x07) + 3
            dist = ((c & 0x03) << 8) | b
            for _ in range(length):
                out += out[-dist : -dist + 1]
        else:
            if pos >= n:
                break
            b = data[pos]
            pos += 1
            length = c >> 5
            if length == 7:
                if pos >= n:
                    break
                length += data[pos]
                pos += 1
            dist = ((c & 0x1F) << 8) | b
            for _ in range(length):
                out += out[-dist : -dist + 1]
    return bytes(out)


def _read_mobi_header(record0: bytes) -> dict:
    idx = record0.find(b"MOBI")
    if idx < 0:
        raise ValueError("Не удалось найти MOBI-заголовок")
    header_len = struct.unpack_from(">I", record0, idx + 4)[0]
    text_encoding = struct.unpack_from(">I", record0, idx + 12)[0]
    exth_start = idx + header_len
    exth: dict[int, list[bytes]] = {}
    if record0[exth_start : exth_start + 4] == b"EXTH":
        count = struct.unpack_from(">I", record0, exth_start + 8)[0]
        off = exth_start + 12
        for _ in range(count):
            if off + 8 > len(record0):
                break
            etype, elen = struct.unpack_from(">II", record0, off)
            if elen < 8:
                break
            exth.setdefault(etype, []).append(record0[off + 8 : off + elen])
            off += elen
    return {"text_encoding": text_encoding, "exth": exth}


def parse_mobi(path: Path) -> ParsedBook:
    data = path.read_bytes()
    if len(data) < 78 or data[60:64] not in (b"BOOK", b"TEXt", b"Palm"):
        if data[60:64] == b"MOBI":
            raise ValueError("Это azw3/azw с неизвестной структурой")
        raise ValueError("Не похоже на книгу MOBI/AZW")
    name = data[:32].split(b"\x00", 1)[0]
    num_records = struct.unpack_from(">H", data, 76)[0]
    if num_records < 2:
        raise ValueError("В книге нет текстовых записей")
    offsets = [
        struct.unpack_from(">I", data, 78 + i * 8)[0] for i in range(num_records)
    ]
    record0 = data[offsets[0] : offsets[1] if num_records > 1 else len(data)]
    meta = _read_mobi_header(record0)
    text_records = []
    for i in range(1, num_records - 1):
        start = offsets[i]
        end = offsets[i + 1] if i + 1 < num_records else len(data)
        text_records.append(data[start:end])
    if not text_records:
        raise ValueError("В книге нет текста")
    payload = b"".join(text_records)
    compression = struct.unpack_from(">H", record0, 0)[0]
    if compression == 2:
        raw_text = _decode_palmdoc(payload)
    elif compression == 1:
        raw_text = payload
    elif compression in (17480, 17481):
        raise ValueError("azw3 с Huffman-сжатием пока не поддерживается")
    else:
        raise ValueError(f"Неизвестное сжатие MOBI: {compression}")
    encoding = _ENCODINGS.get(meta["text_encoding"], "utf-8")
    text = raw_text.replace(b"\x00", b"").replace(b"\x1b", b"").decode(
        encoding, errors="replace"
    )
    title_bytes = (meta["exth"].get(503) or [name])[0]
    author_bytes = meta["exth"].get(100) or []
    title = title_bytes.decode("utf-8", errors="replace").strip() or path.stem
    authors = [
        a.decode("utf-8", errors="replace").strip() for a in author_bytes if a.strip()
    ]
    return ParsedBook(
        format=Format.MOBI,
        title=title,
        authors=authors,
        chapters=parse_html_text(text, title, authors=authors).chapters,
    )
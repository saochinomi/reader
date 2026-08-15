from __future__ import annotations

import re
from pathlib import Path

from ..models import Chapter, Format, ParsedBook
from .txt import _split_chapters

_WORD_RE = re.compile(r"[a-zA-Z]+")
_NUM_RE = re.compile(r"-?\d+")
_HEX_RE = re.compile(r"\\'([0-9a-fA-F]{2})")
_CODEPAGES = {
    "1250": "cp1250",
    "1251": "cp1251",
    "1252": "cp1252",
    "1254": "cp1254",
    "65001": "utf-8",
}


def _code_page(data: str) -> str:
    m = re.search(r"\\ansicpg(\d+)", data[:4096])
    return _CODEPAGES.get(m.group(1), "cp1251") if m else "cp1251"


def _decode_segment(segment: str, code_page: str) -> str:
    def repl(m: re.Match) -> str:
        try:
            return bytes.fromhex(m.group(1)).decode(code_page, errors="replace")
        except ValueError:
            return ""
    return _HEX_RE.sub(repl, segment)


_SKIP_DESTINATIONS = {
    "fonttbl", "stylesheet", "info", "pict", "colortbl", "revtbl",
    "listtable", "listoverridetable", "header", "footer", "footnote",
    "annotation", "themedata", "latentstyles", "generator", "xmlnstbl",
}


def _skip_group(data: str, start: int) -> int:
    depth = 0
    i = start
    n = len(data)
    while i < n:
        if data[i] == "{":
            depth += 1
        elif data[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def _group_is_skippable(data: str, start: int) -> bool:
    i = start + 1
    while i < len(data) and data[i] in " \t\n":
        i += 1
    if data[i : i + 2] == "\\*":
        return True
    if i < len(data) and data[i] == "\\":
        m = _WORD_RE.match(data, i + 1)
        if m:
            return m.group(0).lower() in _SKIP_DESTINATIONS
    return False


def _extract_text(data: str, code_page: str) -> str:
    out: list[str] = []
    i = 0
    n = len(data)
    while i < n:
        ch = data[i]
        if ch == "{":
            if _group_is_skippable(data, i):
                i = _skip_group(data, i)
            else:
                i += 1
            continue
        if ch == "}":
            i += 1
            continue
        if ch == "\\":
            if i + 1 >= n:
                break
            nxt = data[i + 1]
            if nxt == "'":
                m = _HEX_RE.match(data, i)
                if m:
                    out.append(_decode_segment(m.group(0), code_page))
                    i = m.end()
                else:
                    i += 2
            elif nxt == "u":
                m = _NUM_RE.match(data, i + 2)
                if m:
                    code = int(m.group(0))
                    out.append(chr(code & 0xFFFF) if code >= 0 else chr(0x10000 + code))
                    i = m.end()
                    if i < n and data[i] == "'":
                        i += 4
                else:
                    i += 2
            elif nxt in ("\\", "{", "}", " "):
                out.append(" " if nxt == " " else "")
                i += 2
            elif nxt == "\n":
                out.append(" ")
                i += 2
            else:
                m = _WORD_RE.match(data, i + 1)
                if m:
                    word = m.group(0)
                    i = m.end()
                    num = _NUM_RE.match(data, i)
                    has_param = bool(num)
                    if num:
                        i = num.end()
                    if word == "par":
                        out.append("\n")
                    elif word == "line":
                        out.append("\n")
                    elif word == "tab":
                        out.append(" ")
                    if not has_param and i < n and data[i] == " ":
                        i += 1
                else:
                    i += 2
            continue
        if ch == "\n":
            out.append(" ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def _extract_title(data: str, code_page: str) -> str:
    idx = data.find("\\title")
    if idx < 0:
        return ""
    i = idx + len("\\title")
    while i < len(data) and data[i] in " \t\n":
        i += 1
    segment: list[str] = []
    while i < len(data):
        ch = data[i]
        if ch == "}":
            break
        if ch == "\\":
            m = _HEX_RE.match(data, i)
            if m:
                segment.append(m.group(0))
                i = m.end()
                continue
            break
        segment.append(ch)
        i += 1
    return _decode_segment("".join(segment), code_page).strip()


def parse_rtf(path: Path) -> ParsedBook:
    raw = path.read_bytes()
    data = raw.decode("latin-1", errors="replace")
    code_page = _code_page(data)
    text = _extract_text(data, code_page)
    title = _extract_title(data, code_page) or path.stem
    return ParsedBook(
        format=Format.RTF,
        title=title,
        chapters=_split_chapters(text),
    )
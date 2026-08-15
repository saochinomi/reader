from __future__ import annotations

_LETTERS = {
    "R": [
        "██████╗ ",
        "██╔══██╗",
        "██████╔╝",
        "██╔══██╗",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
    "E": [
        "███████╗",
        "██╔════╝",
        "█████╗  ",
        "██╔══╝  ",
        "███████╗",
        "╚══════╝",
    ],
    "A": [
        " █████╗ ",
        "██╔══██╗",
        "███████║",
        "██╔══██║",
        "██║  ██║",
        "╚═╝  ╚═╝",
    ],
    "D": [
        "██████╗ ",
        "██╔══██╗",
        "██║  ██║",
        "██║  ██║",
        "██████╔╝",
        "╚═════╝ ",
    ],
}

_GAP = ""


def banner(word: str = "READER") -> str:
    """Собирает ASCII-баннер (блок-буквы) из переданного слова."""
    letters = [_LETTERS[c] for c in word.upper() if c in _LETTERS]
    if not letters:
        return word
    height = len(letters[0])
    rows = [_GAP.join(letter[r] for letter in letters) for r in range(height)]
    width = max(len(r) for r in rows)
    return "\n".join(r.ljust(width) for r in rows)
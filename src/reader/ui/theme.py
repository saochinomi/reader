from __future__ import annotations

DEFAULT = "green"

# name -> (accent, bright, bg, dim)
PALETTES: dict[str, tuple[str, str, str, str]] = {
    "green": ("#7fbf7f", "#9ece6a", "#1f3a24", "#15231a"),
    "blue": ("#7aa2f7", "#82aaff", "#1a2440", "#14203a"),
    "purple": ("#9d7cd8", "#bb9af7", "#2a1a40", "#221536"),
    "red": ("#f7768e", "#ff7a93", "#401a22", "#33151c"),
    "orange": ("#e0834f", "#ff9e64", "#3a2816", "#2e1f12"),
    "cyan": ("#62b4d4", "#7dcfff", "#16323a", "#11272e"),
    "yellow": ("#c9a94f", "#e0af68", "#3a3316", "#2e2912"),
}

_NAMES: dict[str, str] = {
    "green": "Зелёный",
    "blue": "Синий",
    "purple": "Фиолетовый",
    "red": "Красный",
    "orange": "Оранжевый",
    "cyan": "Бирюзовый",
    "yellow": "Жёлтый",
}


def name(label: str) -> str:
    return _NAMES.get(label, label)


def palette(label: str) -> tuple[str, str, str, str]:
    return PALETTES.get(label, PALETTES[DEFAULT])


def css_variables(label: str) -> str:
    accent, bright, bg, dim = palette(label)
    return (
        f"$primary: {accent};\n"
        f"$accent: {bright};\n"
        f"$accent-bg: {bg};\n"
        f"$accent-dim: {dim};\n"
    )
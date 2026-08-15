from __future__ import annotations

import re

_MARKERS_RE = re.compile(r"^(?:[#*§•]+\s*)+")
_NUMBER_RE = re.compile(r"^\d{1,4}[.)]\s*")


def clean_title(title: str) -> str:
    """Убирает маркеры (#, ##, §, *) и ведущую нумерацию (1., 2)) из названия главы."""
    cleaned = _MARKERS_RE.sub("", title.strip()).strip()
    cleaned = _NUMBER_RE.sub("", cleaned).strip()
    return cleaned
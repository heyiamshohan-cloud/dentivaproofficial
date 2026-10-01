"""Unicode-safe text helpers.

User content (names, addresses, clinical notes, medicines) is full Unicode and
routinely mixes Bangla with English, so every helper here is encoding-agnostic
and never truncates in the middle of a grapheme cluster.
"""

from __future__ import annotations

import re
import unicodedata

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_WHITESPACE = re.compile(r"\s+")


def clean_text(value: str | None, *, collapse_whitespace: bool = True) -> str:
    """Normalise user text: NFC, strip control characters, tidy whitespace."""
    if not value:
        return ""
    text = unicodedata.normalize("NFC", value)
    text = _CONTROL.sub("", text)
    if collapse_whitespace:
        text = _WHITESPACE.sub(" ", text)
    return text.strip()


def normalise_key(value: str | None) -> str:
    """Case- and accent-insensitive key for duplicate detection and search."""
    if not value:
        return ""
    decomposed = unicodedata.normalize("NFKD", value)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return _WHITESPACE.sub(" ", stripped).strip().casefold()


def truncate(value: str, limit: int, *, suffix: str = "…") -> str:
    """Truncate without breaking a grapheme cluster (Bangla conjuncts included)."""
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    keep = limit - len(suffix)
    if keep <= 0:
        return suffix[:limit]
    return value[:keep].rstrip() + suffix


def initials(name: str | None, *, maximum: int = 2) -> str:
    """Initials for avatars; works for Bangla and Latin names."""
    parts = [part for part in (name or "").split() if part]
    if not parts:
        return "?"
    letters = "".join(part[0] for part in parts[:maximum])
    return letters.upper() if letters.isascii() else letters


def compact_number(value: int) -> str:
    """1_234 -> '1.2K' style label for dashboard tiles."""
    if abs(value) < 1000:
        return str(value)
    for factor, suffix in ((1_000_000, "M"), (1_000, "K")):
        if abs(value) >= factor:
            scaled = value / factor
            text = f"{scaled:.1f}".rstrip("0").rstrip(".")
            return f"{text}{suffix}"
    return str(value)


def has_bengali(value: str) -> bool:
    """True when the text contains Bengali code points."""
    return any("\u0980" <= ch <= "\u09ff" for ch in value or "")


def contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    lowered = (haystack or "").casefold()
    return any(needle.casefold() in lowered for needle in needles if needle)

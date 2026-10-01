"""Unicode-safe text helpers (REQ-GEN-003, REQ-BNG-001)."""

from __future__ import annotations

from dentiva.core.textutil import (
    clean_text,
    compact_number,
    contains_any,
    has_bengali,
    initials,
    normalise_key,
    truncate,
)


def test_clean_text_normalises_whitespace_and_control_characters() -> None:
    assert clean_text("মোহাম্মদ  রাহাত\tহোসেন") == "মোহাম্মদ রাহাত হোসেন"
    assert clean_text("bad\x00text") == "badtext"
    assert clean_text(None) == ""


def test_normalise_key_is_case_and_accent_insensitive() -> None:
    assert normalise_key("Rahat") == "rahat"
    assert normalise_key("  RAHAT  Hossain ") == "rahat hossain"
    assert normalise_key("") == ""


def test_truncate_keeps_bangla_intact() -> None:
    result = truncate("দাঁতে ব্যথা ও মাড়ি ফুলা", 8)
    assert result.endswith("…")
    assert len(result) <= 8


def test_initials_work_for_bangla_and_latin() -> None:
    assert initials("Shohan Khan") == "SK"
    assert initials("রাহাত হোসেন") == "রহ"
    assert initials("") == "?"


def test_has_bengali_detects_script() -> None:
    assert has_bengali("দাঁত")
    assert not has_bengali("Tooth")


def test_compact_number_and_contains_any() -> None:
    assert compact_number(950) == "950"
    assert compact_number(1500) == "1.5K"
    assert contains_any("রাহাত হোসেন", ("রাহাত",))
    assert not contains_any("Rahat", ("hossain",))

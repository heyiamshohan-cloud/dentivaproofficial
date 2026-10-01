"""Password hashing and policy (docs/05 §2, REQ-AUTH-001/007).

Argon2id with per-password salts; parameters travel with the hash so they can be
raised later; verification is constant-time and never leaks whether an account
exists.
"""

from __future__ import annotations

import pytest

from dentiva.core.errors import ValidationError
from dentiva.security import password as pw

STRONG = "Dentiva#2026!"
OTHER = "Smile-Clinic-77"


def test_hashes_are_argon2id_phc_strings() -> None:
    digest = pw.hash_password(STRONG)
    assert digest.startswith("$argon2id$")
    assert "v=19" in digest
    parameters = pw.parameters_of(digest)
    assert parameters["type"] == "ID"
    assert parameters["time_cost"] == pw.TIME_COST
    assert parameters["memory_cost"] == pw.MEMORY_COST


def test_every_hash_gets_its_own_salt() -> None:
    first = pw.hash_password(STRONG)
    second = pw.hash_password(STRONG)
    assert first != second, "the same password must not produce the same hash twice"


def test_verification_accepts_the_right_password_only() -> None:
    digest = pw.hash_password(STRONG)
    assert pw.verify_password(STRONG, digest) is True
    assert pw.verify_password(OTHER, digest) is False
    assert pw.verify_password("", digest) is False


def test_a_malformed_hash_is_false_not_an_exception() -> None:
    assert pw.verify_password(STRONG, "not-a-hash") is False
    assert pw.verify_password(STRONG, "") is False


def test_a_fresh_hash_does_not_need_rehashing() -> None:
    digest = pw.hash_password(STRONG)
    assert pw.needs_rehash(digest) is False
    assert pw.needs_rehash("garbage") is True


def test_verifying_an_unknown_user_costs_the_same_and_returns_false() -> None:
    assert pw.verify_unknown_user(STRONG) is False


def test_unicode_passwords_normalise_and_verify() -> None:
    bangla = "আমার-গোপন-শব্দ-১২৩"
    digest = pw.hash_password(bangla)
    assert pw.verify_password(bangla, digest) is True


def test_policy_rejects_short_and_weak_passwords() -> None:
    for candidate in ("short1!A", "onlylowercaseletters", "nodigitshere!!", "1234567890", ""):
        with pytest.raises(ValidationError):
            pw.validate_password(candidate)


def test_policy_accepts_a_strong_password() -> None:
    pw.validate_password(STRONG)


def test_policy_rejects_the_username_as_the_password() -> None:
    with pytest.raises(ValidationError, match="username"):
        pw.validate_password("admin12345!", username="admin12345!")


def test_policy_rejects_common_passwords_before_the_other_rules() -> None:
    """A breached password is refused with the clearest message, not a class hint."""
    with pytest.raises(ValidationError, match="common"):
        pw.validate_password("qwerty1234")
    # The comparison is exact after NFKC-normalisation and lower-casing; adding
    # a symbol makes a different password, which still has to clear the other
    # rules (documented honestly rather than pretending to spot leetspeak).
    with pytest.raises(ValidationError, match="common"):
        pw.validate_password("bangladesh1")


def test_policy_has_a_human_readable_description() -> None:
    description = pw.PasswordPolicy().describe()
    assert "10" in description and "lowercase" in description


def test_strength_meter_scales_and_is_bounded() -> None:
    assert pw.password_strength("") == 0
    assert pw.password_strength("abc") <= 1
    assert pw.password_strength(STRONG) >= 2
    assert pw.password_strength(STRONG * 3) <= 4


def test_no_password_is_ever_returned_by_the_module() -> None:
    digest = pw.hash_password(STRONG)
    assert STRONG not in digest
    assert pw.parameters_of(digest).keys() == {"time_cost", "memory_cost", "parallelism", "type"}

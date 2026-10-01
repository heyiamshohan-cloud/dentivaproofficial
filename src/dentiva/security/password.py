"""Password hashing and policy (docs/05 §2).

Every hash is an **Argon2id** PHC string produced by ``argon2-cffi``. The
parameters travel with the hash, so they can be raised later and old hashes are
silently re-hashed on the next successful login.

The module never logs a password, never stores one, and never compares hashes
with ``==`` — comparison is constant-time inside ``argon2``'s verifier.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any

from argon2 import PasswordHasher, Type
from argon2.exceptions import (
    HashingError,
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)

from dentiva.core.errors import ValidationError

#: Argon2id parameters (docs/05 §2). 64 MiB keeps a login under ~400 ms on the
#: class of hardware a reception desk uses, while remaining expensive to attack.
TIME_COST = 3
MEMORY_COST = 64 * 1024  # KiB
PARALLELISM = 2
HASH_LENGTH = 32
SALT_LENGTH = 16

#: Small local list of passwords that must never be accepted (REQ-SEC-002).
COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "1234567890",
        "123456789",
        "qwerty1234",
        "letmein123",
        "admin12345",
        "welcome123",
        "dentiva123",
        "dental1234",
        "bangladesh1",
        "iloveyou123",
    }
)

_HASHER = PasswordHasher(
    time_cost=TIME_COST,
    memory_cost=MEMORY_COST,
    parallelism=PARALLELISM,
    hash_len=HASH_LENGTH,
    salt_len=SALT_LENGTH,
    type=Type.ID,
)

#: A hash of a value nobody can type. Verified against for unknown usernames so
#: that a missing account costs the same time as a wrong password (no enumeration).
_DUMMY_HASH = "".join(["0"] * 8)


@dataclass(frozen=True, slots=True)
class PasswordPolicy:
    """Clinic-configurable password rules (Settings → Security)."""

    minimum_length: int = 10
    required_classes: int = 3  # of lower, upper, digit, symbol
    reject_username: bool = True
    reject_common: bool = True
    history_size: int = 3

    def describe(self) -> str:
        return (
            f"At least {self.minimum_length} characters, including "
            f"{self.required_classes} of these four: lowercase, uppercase, digit, symbol."
        )


def hash_password(password: str) -> str:
    """Return an Argon2id PHC string for *password*."""
    try:
        return _HASHER.hash(_normalise(password))
    except HashingError as exc:  # pragma: no cover - only on a broken allocator
        raise ValidationError("This password could not be stored.", detail=str(exc)) from exc


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verification. Returns False for a malformed hash."""
    try:
        return _HASHER.verify(password_hash, _normalise(password))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def verify_unknown_user(password: str) -> bool:
    """Burn the same work as a real verification for a non-existent user.

    Prevents user enumeration through timing: the caller must always call this
    when the username does not exist.
    """
    try:
        _HASHER.verify(_dummy_hash(), _normalise(password))
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return False


def needs_rehash(password_hash: str) -> bool:
    """True when the stored hash uses older parameters and should be upgraded."""
    try:
        return _HASHER.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def parameters_of(password_hash: str) -> dict[str, Any]:
    """Parse the parameters embedded in a PHC hash (for display/audit)."""
    try:
        from argon2 import extract_parameters

        params = extract_parameters(password_hash)
    except (InvalidHashError, ImportError):  # pragma: no cover - malformed hash
        return {}
    return {
        "time_cost": getattr(params, "time_cost", None),
        "memory_cost": getattr(params, "memory_cost", None),
        "parallelism": getattr(params, "parallelism", None),
        "type": getattr(getattr(params, "type", None), "name", None),
    }


def validate_password(
    password: str, *, username: str = "", policy: PasswordPolicy | None = None
) -> None:
    """Raise :class:`ValidationError` when *password* does not satisfy *policy*."""
    rules = policy or PasswordPolicy()
    if not password:
        raise ValidationError("Enter a password.")
    # Common passwords are refused first: "this password is too common" tells the
    # user why, whereas the character-class rule would only say what is missing.
    if rules.reject_common and _key(password) in COMMON_PASSWORDS:
        raise ValidationError("This password is too common. Choose a different one.")
    if len(password) < rules.minimum_length:
        raise ValidationError(
            f"Use at least {rules.minimum_length} characters.",
            detail=f"length={len(password)}",
        )
    classes = _character_classes(password)
    if len(classes) < rules.required_classes:
        raise ValidationError(
            f"Include {rules.required_classes} of these four: lowercase, uppercase, digit, symbol.",
            detail=f"found={sorted(classes)}",
        )
    if rules.reject_username and username and password.lower() == username.lower():
        raise ValidationError("The password must not be the same as the username.")


def password_strength(password: str) -> int:
    """0–4 score used only for the strength meter (never for enforcement)."""
    if not password:
        return 0
    score = 0
    if len(password) >= 10:
        score += 1
    if len(password) >= 14:
        score += 1
    if len(_character_classes(password)) >= 3:
        score += 1
    if len(set(password)) >= len(password) * 0.7:
        score += 1
    return min(score, 4)


def _character_classes(password: str) -> set[str]:
    classes: set[str] = set()
    if re.search(r"[a-z]", password):
        classes.add("lower")
    if re.search(r"[A-Z]", password):
        classes.add("upper")
    if re.search(r"\d", password):
        classes.add("digit")
    if re.search(r"[^A-Za-z0-9]", password):
        classes.add("symbol")
    return classes


def _key(password: str) -> str:
    return unicodedata.normalize("NFKC", password).strip().lower()


def _normalise(password: str) -> str:
    """NFKC-normalise so a Bengali/Latin mixed password verifies consistently."""
    return unicodedata.normalize("NFKC", password)


def _dummy_hash() -> str:
    """A syntactically valid hash that can never match a real password."""
    global _DUMMY_HASH
    if "".join(["0"] * 8) == _DUMMY_HASH:
        _DUMMY_HASH = _HASHER.hash("\x00dentiva-unknown-user\x00")
    return _DUMMY_HASH

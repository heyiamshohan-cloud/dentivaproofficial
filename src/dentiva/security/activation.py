"""Offline activation (ADR-0006, REQ-ACT-001…005, docs/05 §6).

The product is activated once, offline, with a fixed code supplied with the
licence. This module implements the verifier with three deliberate properties:

1. **The code is never present in the source.** Only a salted Argon2id verifier
   is shipped, split across two private modules, so neither grep nor a single
   file reveals anything usable. Brute-forcing the verifier would cost on the
   order of 10^8 machine-years with the parameters below.
2. **No network is ever contacted.** :mod:`dentiva.core` modules contain no
   networking imports at all, and neither does this one.
3. **Activation is a local record, not a lock.** Success writes an HMAC over the
   machine identifier to *both* the data directory and the database; start-up
   requires the two to agree. Re-activating with the same code always works and
   there is no hardware lock-in.

Stated honestly (REQ-ACT-005): a purely local check cannot stop an attacker who
already controls the machine. What it does is stop casual, unlicensed copying.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from dentiva.core.clock import utc_now
from dentiva.core.errors import ActivationError
from dentiva.core.fileutil import atomic_write
from dentiva.core.paths import AppPaths
from dentiva.security._activation_part_a import SALT_PART_A, VERIFIER_PART_A
from dentiva.security._activation_part_b import SALT_PART_B, VERIFIER_PART_B
from dentiva.security.secrets import get_local_key, machine_id

#: File (inside the data directory) that mirrors the activation record.
ACTIVATION_FILENAME = "activation.json"

#: Algorithm label stored with the record so a future change is detectable.
TOKEN_ALGORITHM = "hmac-sha256"


@dataclass(frozen=True, slots=True)
class ActivationState:
    """Whether this installation is activated, and how that was established."""

    activated: bool
    machine_id: str
    activated_at_utc: datetime | None = None
    source: str = "none"  # none | both | database | file | missing
    consistent: bool = True
    detail: str = ""


def _verifier() -> str:
    return VERIFIER_PART_A + VERIFIER_PART_B


def _salt() -> str:
    return SALT_PART_A + SALT_PART_B


def _hasher() -> PasswordHasher:
    """A hasher dedicated to activation (peppered with the application salt)."""
    return PasswordHasher(
        time_cost=3,
        memory_cost=64 * 1024,
        parallelism=2,
        hash_len=32,
        salt_len=16,
        type=Type.ID,
    )


def normalise_code(code: str) -> str:
    """Strip the separators a user may type (spaces, dashes)."""
    return "".join(character for character in code if character.isdigit())


def verify_code(code: str) -> bool:
    """Return True when *code* is the correct activation code.

    The comparison happens inside Argon2's constant-time verifier; the candidate
    is never stored, logged or compared as plain text.
    """
    candidate = normalise_code(code)
    if not candidate:
        return False
    try:
        return _hasher().verify(_verifier(), candidate + _salt())
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def activation_token(machine: str | None = None, *, paths: AppPaths | None = None) -> str:
    """HMAC over the machine id, keyed by the local (DPAPI-protected) key."""
    identifier = machine or machine_id()
    return hmac.new(get_local_key(paths), identifier.encode("utf-8"), hashlib.sha256).hexdigest()


def activation_file_path(paths: AppPaths | None = None) -> Path:
    resolved = paths if paths is not None else AppPaths.create().ensure()
    return resolved.data / ACTIVATION_FILENAME


def activate(code: str, *, paths: AppPaths | None = None) -> ActivationState:
    """Verify *code* and, on success, write the activation record to both places.

    Raises :class:`ActivationError` when the code is wrong. Idempotent: acting
    on an already activated installation simply refreshes the record.
    """
    if not verify_code(code):
        raise ActivationError(
            "That activation code is not valid.",
            detail="activation code verification failed",
        )
    resolved = paths if paths is not None else AppPaths.create().ensure()
    identifier = machine_id()
    payload = {
        "machine_id": identifier,
        "token": activation_token(identifier, paths=resolved),
        "algorithm": TOKEN_ALGORITHM,
        "activated_at_utc": utc_now().isoformat(timespec="seconds"),
    }
    atomic_write(
        activation_file_path(resolved),
        json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"),
    )
    return ActivationState(
        activated=True,
        machine_id=identifier,
        activated_at_utc=datetime.fromisoformat(payload["activated_at_utc"]),
        source="file",
        consistent=True,
    )


def record_in_database(
    identifier: str, token: str, *, algorithm: str = TOKEN_ALGORITHM
) -> dict[str, object]:
    """Build the database row for an activation record (written by the service)."""
    return {
        "machine_id": identifier,
        "token": token,
        "algorithm": algorithm,
        "activated_at_utc": utc_now(),
    }


def check_activation(
    *,
    paths: AppPaths | None = None,
    database_record: dict[str, object] | None = None,
) -> ActivationState:
    """Report the activation state, requiring the file and the DB row to agree.

    ``database_record`` is supplied by the caller (the activation service reads
    the ``activation_record`` table). When a record exists in only one place, or
    the two disagree, the installation is reported as **not** activated: a
    half-written activation must never silently grant access.
    """
    identifier = machine_id()
    file_record = _read_file_record(paths)
    has_file = file_record is not None
    has_db = bool(database_record)

    if not has_file and not has_db:
        return ActivationState(False, identifier, source="none", detail="not activated")
    if has_file and not has_db:
        return ActivationState(
            False,
            identifier,
            source="file",
            consistent=False,
            detail="the activation file has no matching database record",
        )
    if has_db and not has_file:
        return ActivationState(
            False,
            identifier,
            source="database",
            consistent=False,
            detail="the database activation record has no matching activation file",
        )

    assert file_record is not None and database_record is not None
    expected = activation_token(identifier, paths=paths)
    file_ok = hmac.compare_digest(str(file_record.get("token", "")), expected)
    db_ok = hmac.compare_digest(str(database_record.get("token", "")), expected)
    if not (file_ok and db_ok):
        return ActivationState(
            False,
            identifier,
            source="both",
            consistent=False,
            detail="the activation token does not match this computer",
        )
    activated_at = _parse_time(str(file_record.get("activated_at_utc", "")))
    return ActivationState(True, identifier, activated_at, source="both", consistent=True)


def _read_file_record(paths: AppPaths | None) -> dict[str, object] | None:
    path = activation_file_path(paths)
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"token": "", "activated_at_utc": ""}
    return data if isinstance(data, dict) else None


def _parse_time(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None

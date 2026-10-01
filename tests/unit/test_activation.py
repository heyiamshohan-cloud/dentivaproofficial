"""Offline activation (docs/05 §6, REQ-ACT-001…005).

The code is verified against a salted Argon2id verifier that is split across two
private modules, so the plaintext exists nowhere in the source. Activation
writes an HMAC of the machine identifier to *both* the data directory and the
database, and start-up requires the two to agree.
"""

from __future__ import annotations

import json

import pytest

from dentiva.core.errors import ActivationError
from dentiva.core.paths import AppPaths
from dentiva.security import activation

#: The code printed on the licence card (docs/05 §6). It is a *fixed* product
#: code, not a secret per customer, which is why the honest scope note matters.
LICENCE_CODE = "1516591935015165"


def test_the_code_verifies_in_every_reasonable_form() -> None:
    assert activation.verify_code(LICENCE_CODE) is True
    assert activation.verify_code(f" {LICENCE_CODE} ") is True
    assert activation.verify_code("1516-5919-3501-5165") is True
    assert activation.verify_code("1516 5919 3501 5165") is True


def test_wrong_codes_are_rejected() -> None:
    for candidate in ("", "0000000000000000", LICENCE_CODE[:-1], LICENCE_CODE + "0"):
        assert activation.verify_code(candidate) is False


def test_normalise_code_strips_formatting() -> None:
    assert activation.normalise_code("1516-5919 3501-5165") == LICENCE_CODE


def test_the_code_never_appears_in_the_source_tree() -> None:
    from pathlib import Path

    import dentiva

    root = Path(dentiva.__file__).resolve().parent
    offenders = [
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if LICENCE_CODE in path.read_text(encoding="utf-8")
    ]
    assert not offenders, f"the activation code is present as plaintext in: {offenders}"


def test_the_verifier_is_split_across_two_modules() -> None:
    from dentiva.security import _activation_part_a, _activation_part_b

    verifier = _activation_part_a.VERIFIER_PART_A + _activation_part_b.VERIFIER_PART_B
    salt = _activation_part_a.SALT_PART_A + _activation_part_b.SALT_PART_B
    assert verifier.startswith("$argon2id$")
    assert LICENCE_CODE not in verifier
    assert LICENCE_CODE not in salt
    assert len(_activation_part_a.VERIFIER_PART_A) > 10
    assert len(_activation_part_b.VERIFIER_PART_B) > 10


def test_the_machine_token_is_stable_and_not_the_code(data_dir) -> None:
    token = activation.activation_token()
    assert token == activation.activation_token()
    assert LICENCE_CODE not in token


def test_activation_writes_the_file_and_reports_success(data_dir) -> None:
    paths = AppPaths.create().ensure()
    state = activation.activate(LICENCE_CODE, paths=paths)
    assert state.activated
    assert state.source == "file"
    written = json.loads(activation.activation_file_path(paths).read_text(encoding="utf-8"))
    assert written["token"] == activation.activation_token(paths=paths)
    assert written["algorithm"] == activation.TOKEN_ALGORITHM
    assert LICENCE_CODE not in json.dumps(written)


def test_a_wrong_code_raises_and_writes_nothing(data_dir) -> None:
    paths = AppPaths.create().ensure()
    with pytest.raises(ActivationError):
        activation.activate("0000000000000000", paths=paths)
    assert not activation.activation_file_path(paths).exists()


def test_activation_is_idempotent(data_dir) -> None:
    paths = AppPaths.create().ensure()
    activation.activate(LICENCE_CODE, paths=paths)
    again = activation.activate(LICENCE_CODE, paths=paths)
    assert again.activated


def test_a_half_written_activation_is_not_accepted(data_dir) -> None:
    paths = AppPaths.create().ensure()
    activation.activate(LICENCE_CODE, paths=paths)
    record = {"token": activation.activation_token(paths=paths)}

    file_only = activation.check_activation(paths=paths, database_record=None)
    assert file_only.activated is False
    assert file_only.consistent is False

    db_only = activation.check_activation(
        paths=AppPaths.create(str(data_dir / "empty")).ensure(), database_record=record
    )
    assert db_only.activated is False
    assert db_only.consistent is False


def test_a_consistent_activation_is_accepted(data_dir) -> None:
    paths = AppPaths.create().ensure()
    activation.activate(LICENCE_CODE, paths=paths)
    record = activation.record_in_database(
        activation.machine_id(), activation.activation_token(paths=paths)
    )
    state = activation.check_activation(paths=paths, database_record=record)
    assert state.activated is True
    assert state.source == "both"
    assert state.consistent is True


def test_a_foreign_token_is_rejected(data_dir) -> None:
    paths = AppPaths.create().ensure()
    activation.activate(LICENCE_CODE, paths=paths)
    state = activation.check_activation(
        paths=paths, database_record={"token": "0" * 64, "machine_id": "other"}
    )
    assert state.activated is False
    assert "does not match" in state.detail


def test_an_unactivated_installation_reports_plainly(data_dir) -> None:
    paths = AppPaths.create(str(data_dir / "fresh")).ensure()
    state = activation.check_activation(paths=paths, database_record=None)
    assert state.activated is False
    assert state.source == "none"
    assert state.detail == "not activated"

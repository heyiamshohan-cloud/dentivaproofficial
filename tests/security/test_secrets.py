"""Local secret material: the key file, sealing and the machine identifier.

docs/05 §1/§7 — the local key protects the activation token and any other
machine-bound secret. This module is deliberately small and offline: no
network, no cloud key escrow, and an honest note about what it does *not*
protect (an administrator who controls the machine).
"""

from __future__ import annotations

import os
import stat
import sys

import pytest

from dentiva.core.paths import AppPaths

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="POSIX permission assertions")


def test_local_key_is_created_once_and_stays_stable(data_dir) -> None:
    from dentiva.security import secrets

    paths = AppPaths.create().ensure()
    first = secrets.get_local_key(paths)
    second = secrets.get_local_key(paths)
    assert first == second, "the local key must not change between calls"
    assert len(first) >= 32, "the key must be long enough to key an HMAC"


def test_key_file_is_only_readable_by_its_owner(data_dir) -> None:
    from dentiva.security import secrets

    paths = AppPaths.create().ensure()
    secrets.get_local_key(paths)
    key_files = sorted(paths.security.glob("*"))
    assert key_files, "a key file must be created"
    mode = stat.S_IMODE(key_files[0].stat().st_mode)
    assert mode & (stat.S_IRWXG | stat.S_IRWXO) == 0, (
        f"key file is group/world accessible: {mode:o}"
    )


def test_seal_and_unseal_round_trip(data_dir) -> None:
    from dentiva.security import secrets

    paths = AppPaths.create().ensure()
    payload = b"dentiva-activation-token-material"
    sealed = secrets.seal(payload, paths=paths)
    assert sealed != payload, "sealing must not return the plaintext unchanged"
    assert payload not in sealed, "the sealed blob must not contain the plaintext"
    assert secrets.unseal(sealed, paths=paths) == payload


def test_unseal_rejects_a_tampered_blob(data_dir) -> None:
    """A flipped byte must be detected, not silently decrypted."""
    from dentiva.core.errors import StorageError
    from dentiva.security import secrets

    paths = AppPaths.create().ensure()
    sealed = bytearray(secrets.seal(b"top secret", paths=paths))
    sealed[-1] ^= 0xFF
    with pytest.raises(StorageError):
        secrets.unseal(bytes(sealed), paths=paths)


def test_machine_id_is_stable_and_not_empty(data_dir) -> None:
    from dentiva.security import secrets

    identifier = secrets.machine_id()
    assert identifier
    assert identifier == secrets.machine_id()
    assert len(identifier) >= 8
    assert "\n" not in identifier and "\x00" not in identifier


def test_no_secret_material_is_written_to_the_logs(data_dir) -> None:
    from dentiva.security import secrets

    paths = AppPaths.create().ensure()
    key = secrets.get_local_key(paths)
    sealed = secrets.seal(b"material", paths=paths)
    log_files = sorted(paths.logs.glob("*.log"))
    blob = "".join(path.read_text(encoding="utf-8", errors="replace") for path in log_files)
    assert key.hex() not in blob
    assert sealed.hex() not in blob


def test_the_module_never_touches_the_network() -> None:
    import inspect

    from dentiva.security import secrets

    source = inspect.getsource(secrets)
    for forbidden in ("socket", "urllib", "requests", "httpx", "http.client"):
        assert forbidden not in source


def test_key_material_is_not_derived_from_the_environment_only(data_dir) -> None:
    """Two different data directories must not produce the same key."""
    from dentiva.core.paths import AppPaths
    from dentiva.security import secrets

    first = secrets.get_local_key(AppPaths.create(str(data_dir / "one")).ensure())
    second = secrets.get_local_key(AppPaths.create(str(data_dir / "two")).ensure())
    assert first != second
    assert os.environ.get("DENTIVA_DATA_DIR")

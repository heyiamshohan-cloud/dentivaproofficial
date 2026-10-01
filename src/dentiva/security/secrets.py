"""Local secret material (docs/05 §1, §7).

The key file lives inside the per-user data directory, is protected with
**DPAPI** on Windows (``CryptProtectData`` through ``ctypes``) and with
restrictive file permissions everywhere else, where a warning is logged.

Honest scope (docs/05 §8): this protects local secrets against *casual*
inspection by another user of the same machine. An administrator with reverse
engineering tooling can always reach local data on their own computer — the
product documentation says so instead of overclaiming.
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import os
import platform
import stat
from pathlib import Path

from dentiva.core.errors import StorageError
from dentiva.core.paths import AppPaths

#: Sub-directory inside the data directory that holds secret material.
SECURITY_DIRNAME = "security"
KEY_FILENAME = "local.key"

#: Length of the random key and of the integrity tag.
KEY_LENGTH = 32
TAG_LENGTH = 32


def local_key_path(paths: AppPaths | None = None) -> Path:
    """Where the local key file lives."""
    resolved = paths if paths is not None else AppPaths.create().ensure()
    return resolved.data / SECURITY_DIRNAME / KEY_FILENAME


def get_local_key(paths: AppPaths | None = None) -> bytes:
    """Return the application key, creating and protecting it on first use."""
    path = local_key_path(paths)
    if path.is_file():
        return _unprotect(path.read_bytes())
    key = os.urandom(KEY_LENGTH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_protect(key))
    _restrict_permissions(path)
    return key


def seal(data: bytes, *, paths: AppPaths | None = None) -> bytes:
    """Return *data* sealed with the local key (keystream + integrity tag).

    Layout: ``tag(32) | nonce(16) | ciphertext``. The tag is computed over the
    nonce and the ciphertext, so a tampered blob is rejected rather than
    silently decrypted into garbage.
    """
    key = get_local_key(paths)
    nonce = os.urandom(16)
    cipher = _xor_stream(key, nonce, len(data))
    encrypted = bytes(a ^ b for a, b in zip(data, cipher, strict=False))
    tag = hmac.new(key, nonce + encrypted, hashlib.sha256).digest()
    return tag + nonce + encrypted


def unseal(blob: bytes, *, paths: AppPaths | None = None) -> bytes:
    """Reverse :func:`seal`; raise :class:`StorageError` on a tampered blob."""
    if len(blob) < TAG_LENGTH + 16:
        raise StorageError("The stored secret is damaged and could not be read.")
    key = get_local_key(paths)
    tag, nonce, encrypted = (
        blob[:TAG_LENGTH],
        blob[TAG_LENGTH : TAG_LENGTH + 16],
        blob[TAG_LENGTH + 16 :],
    )
    expected = hmac.new(key, nonce + encrypted, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise StorageError("The stored secret failed its integrity check.")
    cipher = _xor_stream(key, nonce, len(encrypted))
    return bytes(a ^ b for a, b in zip(encrypted, cipher, strict=False))


def machine_id() -> str:
    """A stable identifier for this installation (never a credential).

    Windows: the machine GUID. Elsewhere: a hash of the host name and the
    account name, which is stable enough for local activation bookkeeping.
    """
    if platform.system() == "Windows":  # pragma: no cover - Windows only
        guid = _windows_machine_guid()
        if guid:
            return guid
    host = platform.node() or "unknown-host"
    account = _account_name()
    return hashlib.sha256(f"{host}|{account}".encode()).hexdigest()[:32]


def _xor_stream(key: bytes, nonce: bytes, length: int) -> bytes:
    """HMAC-SHA256 keystream (counter mode) — avoids a third-party cipher."""
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
        stream.extend(block)
        counter += 1
    return bytes(stream[:length])


def _protect(data: bytes) -> bytes:
    """DPAPI-protect on Windows; store as-is elsewhere (file mode only)."""
    if platform.system() != "Windows":  # pragma: no cover - exercised on Windows CI
        return data
    return _dpapi_protect(data) or data


def _unprotect(blob: bytes) -> bytes:
    if platform.system() != "Windows":  # pragma: no cover - exercised on Windows CI
        return blob
    return _dpapi_unprotect(blob) or blob


def _restrict_permissions(path: Path) -> None:
    """Make the key file readable only by its owner (no-op on Windows)."""
    if platform.system() == "Windows":  # pragma: no cover - Windows only
        return
    # A read-only or exotic filesystem simply keeps the default permissions.
    with contextlib.suppress(OSError):
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _account_name() -> str:
    for variable in ("USER", "USERNAME", "LOGNAME"):
        value = os.environ.get(variable)
        if value:
            return value
    return "unknown-user"


def _windows_machine_guid() -> str:  # pragma: no cover - Windows only
    try:
        import winreg

        # winreg is Windows-only; on other platforms this branch is never reached.
        hive = winreg.HKEY_LOCAL_MACHINE  # type: ignore[attr-defined]
        with winreg.OpenKey(  # type: ignore[attr-defined]
            hive, r"SOFTWARE\Microsoft\Cryptography"
        ) as key:
            value, _type = winreg.QueryValueEx(key, "MachineGuid")  # type: ignore[attr-defined]
        return str(value)
    except Exception:
        return ""


def _dpapi_protect(data: bytes) -> bytes | None:  # pragma: no cover - Windows only
    """Encrypt with CryptProtectData (user scope)."""
    return _dpapi(data, protect=True)


def _dpapi_unprotect(blob: bytes) -> bytes | None:  # pragma: no cover - Windows only
    return _dpapi(blob, protect=False)


def _dpapi(payload: bytes, *, protect: bool) -> bytes | None:  # pragma: no cover
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):  # noqa: N801 - mirrors the Win32 API name
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt = ctypes.windll.crypt32  # type: ignore[attr-defined]
    buffer = ctypes.create_string_buffer(payload)
    source = DATA_BLOB(len(payload), buffer)
    target = DATA_BLOB()
    function = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    try:
        if not function(ctypes.byref(source), None, None, None, None, 0, ctypes.byref(target)):
            return None
        return ctypes.string_at(target.pbData, target.cbData)
    finally:
        if target.pbData:
            ctypes.windll.kernel32.LocalFree(target.pbData)  # type: ignore[attr-defined]

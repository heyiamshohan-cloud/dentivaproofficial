"""Hashing helpers for files and byte streams (SHA-256)."""

from __future__ import annotations

import hashlib
from pathlib import Path

CHUNK_SIZE = 1024 * 1024


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path, *, chunk_size: int = CHUNK_SIZE) -> str:
    """Stream a file through SHA-256 (constant memory for any file size)."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_stream(stream, *, chunk_size: int = CHUNK_SIZE) -> str:
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        digest.update(chunk)
    return digest.hexdigest()

"""SHA-256 helpers used by backups and attachments (REQ-BKP-003)."""

from __future__ import annotations

import io

from dentiva.core.hashing import sha256_bytes, sha256_file, sha256_stream, sha256_text


def test_known_vector() -> None:
    assert sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def test_text_and_streams_match_file(tmp_path) -> None:
    payload = "দাঁতে ব্যথা — tooth pain\nsecond line".encode()
    target = tmp_path / "note.bin"
    target.write_bytes(payload)
    assert sha256_text(payload.decode("utf-8")) == sha256_file(target)
    with open(target, "rb") as handle:
        assert sha256_stream(handle) == sha256_file(target)
    assert sha256_stream(io.BytesIO(payload)) == sha256_file(target)


def test_large_file_hashing_is_streamed(tmp_path) -> None:
    target = tmp_path / "large.bin"
    with open(target, "wb") as handle:
        for _ in range(64):
            handle.write(b"x" * 1024)
    assert len(sha256_file(target, chunk_size=1024)) == 64

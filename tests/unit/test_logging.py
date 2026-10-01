"""Logging: rotation, retention and secret redaction (REQ-LOG-001/002, REQ-SEC-002)."""

from __future__ import annotations

from dentiva.core.logging_setup import configure_logging, get_logger, redact
from dentiva.core.paths import AppPaths


def test_redaction_removes_passwords_and_activation_codes() -> None:
    text = "login failed password=hunter2 activation_code=0000000000000000"
    cleaned = redact(text)
    assert "hunter2" not in cleaned
    assert "0000000000000000" not in cleaned
    assert "«redacted»" in cleaned


def test_redaction_removes_argon2_hashes() -> None:
    cleaned = redact("$argon2id$v=19$m=65536,t=3,p=2$c2FsdA$abc")
    assert "argon2id" not in cleaned


def test_logger_writes_a_rotating_file_without_secrets(tmp_path) -> None:
    paths = AppPaths.create(tmp_path / "data").ensure()
    log_file = configure_logging(paths, console=False)
    assert log_file is not None
    logger = get_logger("test")
    logger.warning("user password=secret123 failed to sign in")
    for handler in logger.handlers:
        handler.flush()
    content = log_file.read_text(encoding="utf-8")
    assert "failed to sign in" in content
    assert "secret123" not in content


def test_logging_survives_an_unwritable_log_directory(tmp_path) -> None:
    """A broken log location must never prevent the application from starting."""
    from dataclasses import replace

    paths = AppPaths.create(tmp_path / "data").ensure()
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory")
    broken = replace(paths, logs=blocker / "logs")
    assert configure_logging(broken, console=False) is None
    assert get_logger("test-missing") is not None


def test_logging_can_be_shut_down_and_the_log_file_released(tmp_path) -> None:
    """Windows will not delete a file that is still open, so the log file has
    to be releasable on demand (self-test, backup, restore, uninstall)."""
    import logging
    from pathlib import Path

    from dentiva.core.logging_setup import (
        LOGGER_NAME,
        configure_logging,
        get_logger,
        shutdown_logging,
    )
    from dentiva.core.paths import AppPaths

    paths = AppPaths.create(tmp_path / "data").ensure()
    log_file = configure_logging(paths, console=False)
    assert log_file is not None
    get_logger("test").info("a line that must be flushed")
    for handler in logging.getLogger(LOGGER_NAME).handlers:
        handler.flush()

    shutdown_logging()
    assert logging.getLogger(LOGGER_NAME).handlers == []
    Path(log_file).unlink()
    assert not Path(log_file).exists()

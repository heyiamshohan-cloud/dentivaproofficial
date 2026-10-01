"""Structured application logging with rotation and secret redaction.

Rules enforced here (REQ-LOG-001/002, REQ-SEC-002):
  * rotating files under ``<data>/logs``, capped in size and count;
  * one line per event, machine parseable prefix;
  * a redaction filter that blanks passwords, hashes, tokens and activation
    material before anything reaches a handler;
  * no patient clinical content is logged — identifiers only.
"""

from __future__ import annotations

import logging
import logging.handlers
import re
from pathlib import Path

from dentiva.core.paths import AppPaths

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s [%(correlation)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
MAX_BYTES = 5 * 1024 * 1024
BACKUP_COUNT = 5
LOGGER_NAME = "dentiva"

#: Keys whose values are always replaced before a record is emitted.
SENSITIVE_KEYS = (
    "password",
    "password_hash",
    "new_password",
    "current_password",
    "token",
    "secret",
    "activation",
    "activation_code",
    "api_key",
    "private_key",
)

_KEY_VALUE = re.compile(
    r"(?i)\b(" + "|".join(SENSITIVE_KEYS) + r")\b\s*[=:]\s*(\"[^\"]*\"|'[^']*'|\S+)"
)
_ARGON2 = re.compile(r"\$argon2[a-z]*\$[^\s'\"]+")
_BEARER = re.compile(r"(?i)\b(bearer|token)\s+[A-Za-z0-9\-._~+/=]{8,}")

REDACTED = "«redacted»"


def redact(text: str) -> str:
    """Remove secrets from *text*. Used by the logging filter and by exports."""
    if not text:
        return text
    text = _ARGON2.sub(REDACTED, text)
    text = _KEY_VALUE.sub(lambda m: f"{m.group(1)}={REDACTED}", text)
    text = _BEARER.sub(lambda m: f"{m.group(1)} {REDACTED}", text)
    return text


class RedactionFilter(logging.Filter):
    """Applies :func:`redact` to the message and every argument."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation = getattr(record, "correlation", "-")
        try:
            record.msg = redact(str(record.msg))
            if record.args:
                if isinstance(record.args, dict):
                    record.args = {
                        key: redact(str(value)) if isinstance(value, (str, bytes)) else value
                        for key, value in record.args.items()
                    }
                else:
                    record.args = tuple(
                        redact(str(arg)) if isinstance(arg, (str, bytes)) else arg
                        for arg in record.args
                    )
        except Exception:  # never let logging break the application
            record.msg = "«log record suppressed by redaction filter»"
            record.args = ()
        return True


class CorrelationFilter(logging.Filter):
    """Injects a correlation id (empty by default) into every record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not getattr(record, "correlation", None):
            record.correlation = "-"
        return True


_configured = False
_handlers: list[logging.Handler] = []


def configure_logging(
    paths: AppPaths | None = None,
    *,
    level: int | str = logging.INFO,
    console: bool = True,
) -> Path | None:
    """Configure the ``dentiva`` logger. Safe to call more than once."""
    global _configured
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    root_filter = RedactionFilter()
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    _handlers.clear()

    file_path: Path | None = None
    if paths is not None:
        try:
            paths.logs.mkdir(parents=True, exist_ok=True)
            file_path = paths.logs / "dentiva.log"
            file_handler = logging.handlers.RotatingFileHandler(
                file_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding="utf-8"
            )
            file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
            file_handler.addFilter(root_filter)
            file_handler.addFilter(CorrelationFilter())
            logger.addHandler(file_handler)
            _handlers.append(file_handler)
        except OSError:
            file_path = None  # logging must never prevent startup

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        console_handler.addFilter(root_filter)
        console_handler.addFilter(CorrelationFilter())
        logger.addHandler(console_handler)
        _handlers.append(console_handler)

    _configured = True
    return file_path


def get_logger(name: str) -> logging.Logger:
    """Return a logger beneath the ``dentiva`` namespace."""
    if not _configured:  # sensible defaults for unit tests and CLI use
        configure_logging(None)
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)


def recent_log_tail(path: str | Path, *, lines: int = 200) -> str:
    """Return the last *lines* of the log file for the diagnostics bundle."""
    log_path = Path(path)
    if not log_path.exists():
        return ""
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    return "\n".join(content[-lines:])

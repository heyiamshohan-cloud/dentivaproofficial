"""Alembic migration environment packaged with the application.

The migration scripts ship inside the package so that a frozen Windows build can
upgrade the clinic database on first launch after an update (see docs/11).
"""

from __future__ import annotations

from pathlib import Path


def script_location() -> Path:
    """Absolute path of the Alembic script directory (dev checkout *or* bundle)."""
    return Path(__file__).resolve().parent

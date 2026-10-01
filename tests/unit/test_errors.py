"""Error hierarchy: user-facing messages, never tracebacks (REQ-ERR-001/002)."""

from __future__ import annotations

from dentiva.core.errors import (
    ConflictError,
    DentivaError,
    NotFound,
    PermissionDenied,
    ValidationError,
)


def test_every_error_exposes_a_safe_message() -> None:
    error = ValidationError("Enter a valid phone number.")
    assert error.user_message() == "Enter a valid phone number."
    assert "Traceback" not in error.user_message()


def test_default_messages_are_meaningful() -> None:
    assert NotFound().user_message()
    assert ConflictError().user_message()
    assert DentivaError().user_message()


def test_permission_denied_keeps_the_permission_code() -> None:
    error = PermissionDenied(permission="invoice.create")
    assert error.permission == "invoice.create"
    assert error.context["permission"] == "invoice.create"


def test_context_is_captured_for_logging() -> None:
    error = ValidationError("Discount too large", max="100")
    assert error.context["max"] == "100"

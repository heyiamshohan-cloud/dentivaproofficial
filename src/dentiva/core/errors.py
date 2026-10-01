"""Central exception hierarchy.

Every error raised by the service layer derives from :class:`DentivaError` and
carries a message that is safe to show to a clinic user. Technical detail belongs
in the logs (see :mod:`dentiva.core.logging_setup`), never in the dialog.
"""

from __future__ import annotations

from typing import Any


class DentivaError(Exception):
    """Base class for all expected Dentiva Pro errors."""

    #: Short, human readable headline shown in the error dialog.
    title = "Something went wrong"
    #: Whether the operation may be retried once the cause is resolved.
    retryable = False

    def __init__(self, message: str = "", *, detail: str = "", **context: Any) -> None:
        self.message = message or self.__doc__ or self.title
        self.detail = detail
        self.context = context
        super().__init__(self.message)

    def user_message(self) -> str:
        """Return the user facing message (never a traceback)."""
        return self.message


class ValidationError(DentivaError):
    """The information entered is not valid."""

    title = "Check the highlighted fields"
    retryable = True


class PermissionDenied(DentivaError):
    """You do not have permission to perform this action."""

    title = "Permission required"
    retryable = False

    def __init__(self, message: str = "", *, permission: str = "", **context: Any) -> None:
        super().__init__(message or self.__doc__ or "", permission=permission, **context)
        self.permission = permission


class AuthenticationRequired(DentivaError):
    """This action requires you to confirm your password."""

    title = "Confirm your password"
    retryable = True


class NotFound(DentivaError):
    """The requested record could not be found."""

    title = "Record not found"
    retryable = False


class ConflictError(DentivaError):
    """The record was changed by someone else, or a duplicate exists."""

    title = "Conflicting change"
    retryable = True


class IntegrityError(DentivaError):
    """This change would break data integrity and was cancelled."""

    title = "Data integrity protection"
    retryable = False


class StorageError(DentivaError):
    """A file or disk operation failed."""

    title = "Storage problem"
    retryable = True


class InsufficientSpaceError(StorageError):
    """There is not enough free disk space for this operation."""

    title = "Not enough disk space"
    retryable = True


class PrintError(DentivaError):
    """The document could not be printed."""

    title = "Printing problem"
    retryable = True


class BackupError(DentivaError):
    """The backup or restore operation failed."""

    title = "Backup problem"
    retryable = True


class ActivationError(DentivaError):
    """The activation code is not valid."""

    title = "Activation required"
    retryable = True


class MigrationError(DentivaError):
    """The database could not be prepared for this version."""

    title = "Database update problem"
    retryable = False

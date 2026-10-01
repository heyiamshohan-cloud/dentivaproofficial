"""First-run activation (docs/05 §6, REQ-ACT-001…005).

The licence code is verified by :mod:`dentiva.security.activation`, which knows
nothing about the database; this service is the other half — it persists the
proof in the ``activation_record`` table and demands that the file and the
database agree before start-up may proceed.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.errors import ActivationError
from dentiva.data.models.ops import ActivationRecord
from dentiva.data.session import session_scope
from dentiva.security import activation
from dentiva.services.rbac import internal, public_operation


@dataclass(frozen=True, slots=True)
class ActivationStatus:
    """Activation state for the splash screen and the About box."""

    activated: bool
    machine_id: str
    activated_at_utc: str | None
    consistent: bool
    detail: str
    masked_machine_id: str

    @property
    def needs_activation(self) -> bool:
        return not self.activated


class ActivationService:
    """Verify the licence code and maintain the activation record."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    @public_operation
    def status(self) -> ActivationStatus:
        """Public (checked before any user exists): the current activation state."""
        with session_scope(self._session_factory) as db:
            row = self._row(db)
            state = activation.check_activation(
                database_record=(
                    {"machine_id": row.machine_id, "token": row.token} if row is not None else None
                )
            )
        return ActivationStatus(
            activated=state.activated,
            machine_id=state.machine_id,
            activated_at_utc=state.activated_at_utc.isoformat() if state.activated_at_utc else None,
            consistent=state.consistent,
            detail=state.detail,
            masked_machine_id=_mask(state.machine_id),
        )

    @public_operation
    def activate(self, code: str) -> ActivationStatus:
        """Verify the code and record activation in both places (idempotent)."""
        state = activation.activate(code)
        with session_scope(self._session_factory) as db:
            db.query(ActivationRecord).delete(synchronize_session=False)
            db.add(
                ActivationRecord(
                    machine_id=state.machine_id,
                    token=activation.activation_token(state.machine_id),
                    algorithm=activation.TOKEN_ALGORITHM,
                    activated_at_utc=state.activated_at_utc,
                )
            )
        return self.status()

    @public_operation
    def activation_hint(self) -> str:
        """Where to look for the code (shown on the activation dialog)."""
        return "The activation code is printed on the licence card supplied with Dentiva Pro."

    @public_operation
    def clear(self) -> None:
        """Remove the activation record (used by the factory-reset flow)."""
        from dentiva.core.paths import AppPaths

        with session_scope(self._session_factory) as db:
            db.query(ActivationRecord).delete(synchronize_session=False)
        path = activation.activation_file_path(AppPaths.create().ensure())
        if path.is_file():
            path.unlink()

    @internal
    def require_activated(self) -> ActivationStatus:
        """Used at start-up: raise unless the installation is fully activated."""
        status = self.status()
        if not status.activated:
            raise ActivationError(
                "Dentiva Pro is not activated on this computer. Enter the licence code to continue."
            )
        return status

    def _row(self, db: DBSession) -> ActivationRecord | None:
        return db.execute(
            select(ActivationRecord).order_by(ActivationRecord.id.desc()).limit(1)
        ).scalar_one_or_none()


def _mask(machine: str) -> str:
    """Show enough of the machine id for support, not enough to clone it."""
    if len(machine) <= 8:
        return machine
    return f"{machine[:4]}…{machine[-4:]}"

"""User accounts: creation, editing, activation and lock-out clearance
(docs/05 §1, REQ-SEC-005…007).

Every operation is sensitive (``user.manage``), so the service layer demands a
fresh password confirmation before anything happens.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import utc_now
from dentiva.core.errors import NotFound, ValidationError
from dentiva.data.models.security import User, UserRole
from dentiva.security import password as password_rules
from dentiva.services.rbac import require

#: Auto-lock choices offered to a user, in minutes.
AUTO_LOCK_OPTIONS = (5, 10, 15, 30)


@dataclass(frozen=True, slots=True)
class UserSummary:
    """A user account as shown on the administration screen."""

    id: int
    username: str
    display_name: str
    is_active: bool
    is_system_admin: bool
    must_change_password: bool
    locked: bool
    session_timeout_minutes: int
    roles: tuple[str, ...]
    last_login_at_utc: str | None


class UserService:
    """Manage login identities (never their clinical records)."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------ reads --
    @require("user.view", action="user.list", entity="user")
    def list_users(
        self,
        db: DBSession,
        *,
        search: str = "",
        include_inactive: bool = False,
    ) -> list[UserSummary]:
        """List accounts, optionally filtered by username or display name."""
        statement = select(User).order_by(User.username)
        if not include_inactive:
            statement = statement.where(User.is_active.is_(True))
        if term := (search or "").strip():
            pattern = f"%{term.lower()}%"
            statement = statement.where(
                or_(
                    func.lower(User.username).like(pattern),
                    func.lower(func.coalesce(User.display_name, "")).like(pattern),
                )
            )
        return [
            self._summarise(user, self._roles(db, user.id))
            for user in db.execute(statement).scalars()
        ]

    @require("user.view", action="user.get", entity="user", entity_id_arg="user_id")
    def get_user(self, db: DBSession, *, user_id: int) -> UserSummary:
        """One account with its roles."""
        user = db.get(User, user_id)
        if user is None:
            raise NotFound("That user no longer exists.")
        return self._summarise(user, self._roles(db, user_id))

    # ----------------------------------------------------------------- writes --
    @require("user.manage", action="user.create", entity="user")
    def create_user(
        self,
        db: DBSession,
        *,
        username: str,
        password: str,
        display_name: str = "",
        role_ids: list[int] | None = None,
        must_change_password: bool = True,
    ) -> UserSummary:
        """Create a login identity. Accounts can never be hard-deleted."""
        clean = (username or "").strip()
        if not clean:
            raise ValidationError("Give the account a username.")
        if len(clean) < 3:
            raise ValidationError("A username must be at least three characters long.")
        clash = db.execute(
            select(User).where(func.lower(User.username) == func.lower(clean))
        ).scalar_one_or_none()
        if clash is not None:
            raise ValidationError(f"The username '{clean}' is already taken.")
        password_rules.validate_password(password, username=clean)
        user = User(
            username=clean,
            password_hash=password_rules.hash_password(password),
            password_algo="argon2id",
            password_updated_at_utc=utc_now(),
            display_name=(display_name or "").strip() or clean,
            is_active=True,
            is_system_admin=False,
            must_change_password=must_change_password,
        )
        db.add(user)
        db.flush()
        for role_id in role_ids or []:
            db.add(UserRole(user_id=user.id, role_id=role_id))
        db.flush()
        return self._summarise(user, self._roles(db, user.id))

    @require("user.manage", action="user.update", entity="user", entity_id_arg="user_id")
    def update_user(
        self,
        db: DBSession,
        *,
        user_id: int,
        display_name: str,
        session_timeout_minutes: int | None = None,
    ) -> UserSummary:
        """Edit the safe fields of an account (the username is immutable)."""
        user = db.get(User, user_id)
        if user is None:
            raise NotFound("That user no longer exists.")
        if session_timeout_minutes is not None and session_timeout_minutes not in AUTO_LOCK_OPTIONS:
            raise ValidationError(
                "Choose an auto-lock time of "
                + ", ".join(str(minutes) for minutes in AUTO_LOCK_OPTIONS)
                + " minutes."
            )
        user.display_name = (display_name or "").strip() or user.username
        user.session_timeout_minutes = session_timeout_minutes
        db.flush()
        return self._summarise(user, self._roles(db, user_id))

    @require("user.manage", action="user.deactivate", entity="user", entity_id_arg="user_id")
    def deactivate_user(self, db: DBSession, *, user_id: int) -> UserSummary:
        """Deactivate an account; it keeps its history and can be re-activated."""
        user = db.get(User, user_id)
        if user is None:
            raise NotFound("That user no longer exists.")
        if user.is_system_admin and self._is_last_admin(db):
            raise ValidationError("The last administrator account cannot be deactivated.")
        user.is_active = False
        db.flush()
        return self._summarise(user, self._roles(db, user_id))

    @require("user.manage", action="user.reactivate", entity="user", entity_id_arg="user_id")
    def reactivate_user(self, db: DBSession, *, user_id: int) -> UserSummary:
        """Re-activate a deactivated account."""
        user = db.get(User, user_id)
        if user is None:
            raise NotFound("That user no longer exists.")
        user.is_active = True
        db.flush()
        return self._summarise(user, self._roles(db, user_id))

    @require("user.manage", action="user.unlock", entity="user", entity_id_arg="user_id")
    def unlock_user(self, db: DBSession, *, user_id: int) -> UserSummary:
        """Clear throttling after repeated failed sign-in attempts."""
        user = db.get(User, user_id)
        if user is None:
            raise NotFound("That user no longer exists.")
        user.failed_attempts = 0
        user.locked_until_utc = None
        db.flush()
        return self._summarise(user, self._roles(db, user_id))

    # ---------------------------------------------------------------- internals --
    def _roles(self, db: DBSession, user_id: int) -> tuple[str, ...]:
        from dentiva.data.models.security import Role

        return tuple(
            db.execute(
                select(Role.name)
                .join(UserRole, UserRole.role_id == Role.id)
                .where(UserRole.user_id == user_id)
                .order_by(Role.name)
            )
            .scalars()
            .all()
        )

    def _is_last_admin(self, db: DBSession) -> bool:
        count = db.execute(
            select(func.count(User.id)).where(
                User.is_system_admin.is_(True), User.is_active.is_(True)
            )
        ).scalar_one()
        return int(count) <= 1

    def _summarise(self, user: User, roles: tuple[str, ...]) -> UserSummary:
        locked = bool(user.locked_until_utc and user.locked_until_utc > utc_now())
        return UserSummary(
            id=user.id,
            username=user.username,
            display_name=user.display_name or user.username,
            is_active=bool(user.is_active),
            is_system_admin=bool(user.is_system_admin),
            must_change_password=bool(user.must_change_password),
            locked=locked,
            session_timeout_minutes=int(user.session_timeout_minutes or 15),
            roles=roles,
            last_login_at_utc=user.last_login_at_utc.isoformat()
            if user.last_login_at_utc
            else None,
        )

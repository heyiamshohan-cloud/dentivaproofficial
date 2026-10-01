"""Authentication, session lifecycle, lock/unlock and password changes
(docs/05 §2-3, REQ-AUTH-001…006).

Throttling: five failed attempts lock the account for one minute, doubling up to
a fifteen-minute ceiling. Verification of an unknown username performs the same
Argon2id work as a real login, so the response time cannot be used to discover
which accounts exist.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import utc_now
from dentiva.core.errors import (
    AuthenticationRequired,
    NotFound,
    ValidationError,
)
from dentiva.data.models.security import PasswordHistory, SessionRecord, User
from dentiva.data.session import session_scope
from dentiva.security import password as password_rules
from dentiva.security.session import REAUTH_VALID_MINUTES, Session, new_session_id
from dentiva.services.audit_service import SEVERITY_SECURITY, AuditService
from dentiva.services.rbac import internal, public_operation, require

#: Throttling policy (docs/05 §2).
MAX_FAILED_ATTEMPTS = 5
INITIAL_LOCKOUT_SECONDS = 60
MAX_LOCKOUT_SECONDS = 15 * 60

#: The session id chosen for the sign-in in progress, so the ``session_record``
#: row and the in-memory :class:`Session` carry the same identifier.
_PENDING_SESSION_ID: contextvars.ContextVar[str] = contextvars.ContextVar(
    "dentiva_pending_session_id", default=""
)

#: How many previous hashes are remembered (and therefore refused).
PASSWORD_HISTORY_SIZE = 3


@dataclass(frozen=True, slots=True)
class LoginResult:
    """Outcome of a sign-in attempt."""

    session: Session
    must_change_password: bool
    display_name: str


@dataclass(frozen=True, slots=True)
class AttemptedUser:
    """The identity a failed sign-in claimed, for the audit trail."""

    username: str
    user_id: None = None
    roles: tuple[str, ...] = ()
    business_id: None = None
    session_id: None = None


_AttemptedUser = AttemptedUser


@dataclass(frozen=True, slots=True)
class FailedLogin:
    """Why a sign-in attempt was refused (no detail leaks whether the user exists)."""

    reason: str  # bad_credentials | locked | inactive
    retry_after_seconds: int = 0
    message: str = "The username or password is not correct."


class AuthService:
    """Sign-in, sign-out, lock/unlock and credential changes."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------ sign in/out --
    @public_operation
    def login(
        self, username: str, password: str, *, app_version: str = ""
    ) -> LoginResult | FailedLogin:
        """Verify credentials and open a session (public: no session exists yet)."""
        username = (username or "").strip()
        if not username or not password:
            return FailedLogin("bad_credentials", message="Enter a username and a password.")
        with session_scope(self._session_factory) as db:
            user = self._user_by_username(db, username)
            if user is None:
                # Spend the same work as a real verification: no enumeration.
                password_rules.verify_unknown_user(password)
                self._audit(
                    db,
                    actor=None,
                    username=username,
                    action="security.login.failed",
                    summary="Sign-in failed: no such account.",
                )
                return FailedLogin("bad_credentials")
            locked_for = self._lockout_remaining(user)
            if locked_for:
                return FailedLogin(
                    "locked",
                    retry_after_seconds=locked_for,
                    message=(
                        f"Too many failed attempts. Try again in {locked_for // 60 + 1} minute(s)."
                    ),
                )
            if not user.is_active:
                self._audit(
                    db,
                    actor=None,
                    username=username,
                    action="security.login.failed",
                    summary="Sign-in refused: the account is not active.",
                )
                return FailedLogin("inactive", message="This account is not active.")
            if not password_rules.verify_password(password, user.password_hash):
                self._register_failure(db, user)
                self._audit(
                    db,
                    actor=None,
                    username=username,
                    action="security.login.failed",
                    summary="Sign-in failed: wrong password.",
                )
                return FailedLogin("bad_credentials")
            pending = new_session_id()
            _PENDING_SESSION_ID.set(pending)
            self._register_success(db, user, password=password, app_version=app_version)
            session = self._build_session(db, user)
            self._audit(
                db,
                actor=session,
                username=user.username,
                action="security.login",
                summary=f"{session.display_name} signed in.",
            )
            db.commit()
            return LoginResult(
                session=session,
                must_change_password=bool(user.must_change_password),
                display_name=user.display_name or user.username,
            )

    @internal
    def logout(self, session: Session) -> None:
        """Close the session record (the caller clears the current session)."""
        with session_scope(self._session_factory) as db:
            record = self._open_record(db, session.session_id)
            if record is not None:
                record.ended_at_utc = utc_now()
                record.end_reason = "logout"

    @internal
    def lock(self, session: Session) -> None:
        """Mark the session locked in the audit trail (work is never lost)."""
        with session_scope(self._session_factory) as db:
            record = self._open_record(db, session.session_id)
            if record is not None:
                record.end_reason = "locked"
                record.ended_at_utc = utc_now()

    @internal
    def unlock(self, session: Session, password: str) -> Session:
        """Re-verify the signed-in user's password and unlock (REQ-AUTH-005)."""
        with session_scope(self._session_factory) as db:
            user = db.get(User, session.user_id)
            if user is None or not user.is_active:
                raise AuthenticationRequired(
                    "This session is no longer valid. Please sign in again."
                )
            locked_for = self._lockout_remaining(user)
            if locked_for:
                raise AuthenticationRequired(
                    f"Too many failed attempts. Try again in {locked_for // 60 + 1} minute(s)."
                )
            if not password_rules.verify_password(password, user.password_hash):
                self._register_failure(db, user)
                raise AuthenticationRequired("That password is not correct.")
            self._clear_failures(db, user)
            session = session.unlock()
            db.commit()
            return session

    @internal
    def reauthenticate(self, session: Session, password: str) -> Session:
        """Confirm the password for a sensitive action (valid for a few minutes)."""
        with session_scope(self._session_factory) as db:
            user = db.get(User, session.user_id)
            if user is None or not user.is_active:
                raise AuthenticationRequired("Please sign in again to continue.")
            if not password_rules.verify_password(password, user.password_hash):
                self._register_failure(db, user)
                raise AuthenticationRequired("That password is not correct.")
            self._clear_failures(db, user)
            return session.grant_reauthentication()

    # -------------------------------------------------------------- passwords --
    @require("user.manage", action="user.password.change", entity="user", entity_id_arg="user_id")
    def change_password(
        self, db: DBSession, *, user_id: int, current_password: str, new_password: str
    ) -> None:
        """Change a password, enforcing policy and password history."""
        user = db.get(User, user_id)
        if user is None:
            raise NotFound("That user no longer exists.")
        if not password_rules.verify_password(current_password, user.password_hash):
            raise ValidationError("The current password is not correct.")
        self._apply_new_password(db, user, new_password)

    @require("user.manage", action="user.password.reset", entity="user", entity_id_arg="user_id")
    def reset_password(
        self, db: DBSession, *, user_id: int, new_password: str, must_change: bool = True
    ) -> None:
        """An administrator resets another user's password (audited)."""
        user = db.get(User, user_id)
        if user is None:
            raise NotFound("That user no longer exists.")
        self._apply_new_password(db, user, new_password)
        user.must_change_password = must_change

    @internal
    def validate_new_password(self, *, username: str, new_password: str) -> None:
        """Expose the policy to the UI before it submits."""
        password_rules.validate_password(new_password, username=username)

    # ----------------------------------------------------------------- internals --
    def _apply_new_password(self, db: DBSession, user: User, new_password: str) -> None:
        password_rules.validate_password(new_password, username=user.username)
        if self._in_password_history(db, user, new_password):
            raise ValidationError("That password was used recently. Choose a different one.")
        user.password_hash = password_rules.hash_password(new_password)
        user.password_algo = "argon2id"
        user.password_updated_at_utc = utc_now()
        user.must_change_password = False
        db.add(
            PasswordHistory(
                user_id=user.id,
                password_hash=user.password_hash,
                created_at_utc=utc_now(),
            )
        )
        self._trim_password_history(db, user)

    def _in_password_history(self, db: DBSession, user: User, candidate: str) -> bool:
        rows = (
            db.execute(
                select(PasswordHistory.password_hash)
                .where(PasswordHistory.user_id == user.id)
                .order_by(PasswordHistory.id.desc())
                .limit(PASSWORD_HISTORY_SIZE)
            )
            .scalars()
            .all()
        )
        return any(password_rules.verify_password(candidate, stored) for stored in rows)

    def _trim_password_history(self, db: DBSession, user: User) -> None:
        keep = (
            db.execute(
                select(PasswordHistory.id)
                .where(PasswordHistory.user_id == user.id)
                .order_by(PasswordHistory.id.desc())
                .limit(PASSWORD_HISTORY_SIZE)
            )
            .scalars()
            .all()
        )
        if not keep:
            return
        db.query(PasswordHistory).filter(
            PasswordHistory.user_id == user.id, PasswordHistory.id.notin_(keep)
        ).delete(synchronize_session=False)

    def _audit(
        self,
        db: DBSession,
        *,
        actor: Session | None,
        username: str,
        action: str,
        summary: str,
    ) -> None:
        """Record a sign-in outcome (the audit service joins this transaction)."""
        AuditService().record(
            db,
            action=action,
            entity="user",
            summary=summary,
            severity=SEVERITY_SECURITY,
            actor=actor or _AttemptedUser(username),
            source="auth",
            business_id=actor.business_id if actor is not None else None,
        )

    def _register_failure(self, db: DBSession, user: User) -> None:
        user.failed_attempts = int(user.failed_attempts or 0) + 1
        if user.failed_attempts >= MAX_FAILED_ATTEMPTS:
            over = max(0, user.failed_attempts - MAX_FAILED_ATTEMPTS)
            seconds = min(INITIAL_LOCKOUT_SECONDS * (2**over), MAX_LOCKOUT_SECONDS)
            user.locked_until_utc = utc_now() + timedelta(seconds=seconds)
        db.flush()

    def _clear_failures(self, db: DBSession, user: User) -> None:
        user.failed_attempts = 0
        user.locked_until_utc = None
        db.flush()

    def _register_success(
        self,
        db: DBSession,
        user: User,
        *,
        password: str,
        app_version: str,
    ) -> None:
        self._clear_failures(db, user)
        if password_rules.needs_rehash(user.password_hash):
            # Silent upgrade: the parameters were raised since this user's last
            # login, so store a fresh hash at the current cost.
            user.password_hash = password_rules.hash_password(password)
            user.password_algo = "argon2id"
            user.password_updated_at_utc = utc_now()
        user.last_login_at_utc = utc_now()
        db.add(
            SessionRecord(
                user_id=user.id,
                session_id=_current_session_id(),
                started_at_utc=utc_now(),
                host=_host_name(),
                app_version=app_version or None,
            )
        )
        db.flush()

    def _lockout_remaining(self, user: User) -> int:
        if not user.locked_until_utc:
            return 0
        remaining = (user.locked_until_utc - utc_now()).total_seconds()
        return int(remaining) if remaining > 0 else 0

    def _user_by_username(self, db: DBSession, username: str) -> User | None:
        normalised = username.strip()
        return db.execute(
            select(User).where(func.lower(User.username) == func.lower(normalised))
        ).scalar_one_or_none()

    def _build_session(self, db: DBSession, user: User) -> Session:
        from dentiva.services.role_service import RoleService

        roles = RoleService(self._session_factory)
        role_names = roles.role_names_for(db, user.id)
        permissions = roles.permissions_for(db, user.id)
        session_id = _PENDING_SESSION_ID.get()
        return Session(
            session_id=session_id,
            user_id=user.id,
            username=user.username,
            display_name=user.display_name or user.username,
            roles=tuple(role_names),
            permissions=permissions,
            business_id=roles.business_id_for(db, user),
            is_system_admin=bool(user.is_system_admin),
            timeout_minutes=user.session_timeout_minutes or 15,
            started_at=utc_now(),
            last_activity_at=utc_now(),
            reauthenticated_at=None,
            locked=False,
        )

    def _open_record(self, db: DBSession, session_id: str) -> SessionRecord | None:
        return db.execute(
            select(SessionRecord).where(
                SessionRecord.session_id == session_id,
                SessionRecord.ended_at_utc.is_(None),
            )
        ).scalar_one_or_none()


def reauth_validity_minutes() -> int:
    """How long a re-authentication stays valid (exposed for the UI hint)."""
    return REAUTH_VALID_MINUTES


def _host_name() -> str:
    import platform

    return platform.node() or "unknown"


def _current_session_id() -> str:
    return _PENDING_SESSION_ID.get()

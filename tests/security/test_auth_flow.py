"""Sign-in, throttling, lock/unlock and password changes (REQ-AUTH-001…007).

These are the behaviours a reception desk relies on every morning: the right
password gets you in, repeated failures lock the account briefly, and changing a
password cannot reuse one you had recently.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from dentiva.core.clock import utc_now
from dentiva.core.errors import AuthenticationRequired, ValidationError
from dentiva.data.models.security import User
from dentiva.data.session import session_scope
from dentiva.security.session import Session, current, set_current
from dentiva.services.audit_service import AuditService
from dentiva.services.auth_service import MAX_FAILED_ATTEMPTS

GOOD = "Dentiva#2026!"
BETTER = "Smile-Clinic-77!"
THIRD = "Ortho-Desk-2049!"


@pytest.fixture(autouse=True)
def _signed_out() -> None:
    yield
    set_current(None)


def test_a_correct_password_opens_a_session(services, clinic) -> None:
    result = services.auth.login("admin", GOOD)
    session = getattr(result, "session", None)
    assert isinstance(session, Session)
    assert session.username == "admin"
    assert session.is_system_admin is True
    assert "patient.view" in session.permissions
    assert result.must_change_password is False


def test_a_wrong_password_is_refused_without_saying_which_part(clinic, services) -> None:
    result = services.auth.login("admin", "wrong-password")
    assert isinstance(result, type(services.auth.login("nobody", "x")))
    assert getattr(result, "session", None) is None
    assert result.reason == "bad_credentials"
    assert "admin" not in result.message.lower()


def test_an_unknown_user_costs_the_same_as_a_wrong_password(clinic, services) -> None:
    unknown = services.auth.login("ghost", GOOD)
    assert getattr(unknown, "session", None) is None
    assert unknown.reason == "bad_credentials"


def test_failures_are_throttled_and_lock_the_account(clinic, services) -> None:
    for _ in range(MAX_FAILED_ATTEMPTS):
        services.auth.login("admin", "definitely-wrong")
    locked = services.auth.login("admin", GOOD)
    assert locked.reason == "locked"
    # The lock is one minute; a few hundred milliseconds of Argon2 work is
    # already spent when the countdown is read back.
    assert 50 <= locked.retry_after_seconds <= 60


def test_a_successful_sign_in_clears_the_counter(clinic, services) -> None:
    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        services.auth.login("admin", "nope")
    result = services.auth.login("admin", GOOD)
    assert getattr(result, "session", None) is not None
    with session_scope(services.session_factory) as db:
        user = db.query(User).filter(User.username == "admin").one()
        assert user.failed_attempts == 0
        assert user.locked_until_utc is None


def test_an_inactive_account_cannot_sign_in(clinic, services) -> None:
    admin = services.auth.login("admin", GOOD).session
    set_current(admin.grant_reauthentication())
    user = services.users.create_user(username="reception", password=GOOD, display_name="Reception")
    services.users.deactivate_user(user_id=user.id)
    set_current(None)
    refused = services.auth.login("reception", GOOD)
    assert refused.reason == "inactive"
    assert "not active" in refused.message


def test_sign_in_and_failure_are_both_audited(clinic, services) -> None:
    services.auth.login("admin", GOOD)
    services.auth.login("admin", "wrong")
    with session_scope(services.session_factory) as db:
        page = AuditService().search(db)
    actions = [entry.action for entry in page.items]
    assert "security.login" in actions
    assert actions.count("security.login.failed") >= 1


def test_unlock_needs_the_password(clinic, services) -> None:
    session = services.auth.login("admin", GOOD).session
    locked = session.lock()
    with pytest.raises(AuthenticationRequired):
        services.auth.unlock(locked, "not-the-password")
    unlocked = services.auth.unlock(locked, GOOD)
    assert unlocked.locked is False


def test_reauthentication_is_required_and_then_valid(clinic, services) -> None:
    session = services.auth.login("admin", GOOD).session
    with pytest.raises(AuthenticationRequired):
        services.auth.reauthenticate(session, "nope")
    fresh = services.auth.reauthenticate(session, GOOD)
    assert fresh.is_reauthentication_valid() is True


def test_changing_a_password_verifies_the_old_one(clinic, services) -> None:
    session = services.auth.login("admin", GOOD).session
    set_current(session.grant_reauthentication())
    with pytest.raises(ValidationError, match="current password"):
        services.auth.change_password(
            user_id=session.user_id, current_password="wrong", new_password=BETTER
        )


def test_a_changed_password_works_and_cannot_be_reused(clinic, services) -> None:
    session = services.auth.login("admin", GOOD).session
    set_current(session.grant_reauthentication())
    services.auth.change_password(
        user_id=session.user_id, current_password=GOOD, new_password=BETTER
    )
    set_current(None)
    assert getattr(services.auth.login("admin", BETTER), "session", None) is not None

    again = services.auth.login("admin", BETTER).session
    set_current(again.grant_reauthentication())
    # The password in use is always in the history, so re-submitting it is refused.
    with pytest.raises(ValidationError, match="used recently"):
        services.auth.change_password(
            user_id=again.user_id, current_password=BETTER, new_password=BETTER
        )
    services.auth.change_password(
        user_id=again.user_id, current_password=BETTER, new_password=THIRD
    )
    third = services.auth.login("admin", THIRD).session
    set_current(third.grant_reauthentication())
    with pytest.raises(ValidationError, match="used recently"):
        services.auth.change_password(
            user_id=third.user_id, current_password=THIRD, new_password=BETTER
        )


def test_an_administrator_can_reset_another_users_password(clinic, services) -> None:
    session = services.auth.login("admin", GOOD).session
    set_current(session.grant_reauthentication())
    user = services.users.create_user(username="reception", password=GOOD, display_name="Reception")
    services.auth.reset_password(user_id=user.id, new_password=BETTER)
    set_current(None)
    assert getattr(services.auth.login("reception", BETTER), "session", None) is not None
    assert getattr(services.auth.login("reception", BETTER), "must_change_password", None) is True


def test_logout_records_the_session_end(clinic, services) -> None:
    session = services.auth.login("admin", GOOD).session
    services.auth.logout(session)
    with session_scope(services.session_factory) as db:
        from dentiva.data.models.security import SessionRecord

        record = (
            db.query(SessionRecord).filter(SessionRecord.session_id == session.session_id).one()
        )
    assert record.ended_at_utc is not None
    assert record.end_reason == "logout"


def test_a_stale_lock_expires_on_its_own(clinic, services) -> None:
    for _ in range(MAX_FAILED_ATTEMPTS):
        services.auth.login("admin", "nope")
    with session_scope(services.session_factory) as db:
        user = db.query(User).filter(User.username == "admin").one()
        user.locked_until_utc = utc_now() - timedelta(seconds=1)
    assert getattr(services.auth.login("admin", GOOD), "session", None) is not None


def test_the_current_session_is_not_leaked_between_tests() -> None:
    assert current() is None

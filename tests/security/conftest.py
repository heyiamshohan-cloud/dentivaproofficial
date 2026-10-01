"""Fixtures for the security suite: a real clinic database and real sessions.

Nothing here mocks the service layer. The permission matrix is made of the
service objects the application itself builds, so a test that passes really is
exercising the same code path a user's click would take.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

import pytest

from dentiva.core.clock import utc_now
from dentiva.data.engine import create_engine_for, upgrade
from dentiva.security.session import Session, set_current
from dentiva.services import Services

#: The licence code used by the security suite (never a secret: it is the code
#: printed on the licence card; only its verifier ships in the source).
ACTIVATION_CODE = "1516591935015165"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "Dentiva#2026!"

CLINIC_NAME = "Smile Dental Care"


@pytest.fixture()
def security_engine(tmp_path):  # type: ignore[no-untyped-def]
    """A migrated, empty clinic database (one per test)."""
    engine = create_engine_for(tmp_path / "security.db")
    upgrade(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def services(security_engine):  # type: ignore[no-untyped-def]
    """Every service wired to the test database."""
    return Services.create(security_engine, app_version="0.0.0-test")


@pytest.fixture()
def clinic(services) -> int:  # type: ignore[no-untyped-def]
    """An activated, set-up clinic; returns the business id."""
    services.activation.activate(ACTIVATION_CODE)
    services.bootstrap.initialise(
        clinic_name=CLINIC_NAME,
        admin_username=ADMIN_USERNAME,
        admin_password=ADMIN_PASSWORD,
        admin_full_name="Clinic Administrator",
        dentist_name="Dr. Shohan",
    )
    with services.session_factory() as db:
        from dentiva.data.models.identity import Business

        business = db.query(Business).order_by(Business.id).first()
        assert business is not None
        return int(business.id)


@pytest.fixture()
def admin_session(services, clinic) -> Iterator[Session]:  # type: ignore[no-untyped-def]
    """Sign the administrator in and make them the current actor."""
    assert clinic > 0, "the clinic must be set up before anyone can sign in"
    result = services.auth.login(ADMIN_USERNAME, ADMIN_PASSWORD)
    session = getattr(result, "session", None)
    assert isinstance(session, Session), result
    set_current(session)
    yield session
    set_current(None)


@pytest.fixture()
def as_actor() -> Callable[..., Any]:
    """Build a session carrying only the given permissions."""

    @contextmanager
    def _actor(*, permissions: frozenset[str] | set[str], name: str = "tester", user_id: int = 7):
        session = Session(
            session_id=f"test-{name}",
            user_id=user_id,
            username=name,
            display_name=name,
            roles=(name.title(),),
            permissions=frozenset(permissions),
            business_id=1,
            is_system_admin=False,
            timeout_minutes=15,
            started_at=utc_now(),
            last_activity_at=utc_now(),
            reauthenticated_at=None,
            locked=False,
        )
        from dentiva.security.session import current

        previous = current()
        set_current(session)
        try:
            yield session
        finally:
            set_current(previous)

    return _actor


@pytest.fixture()
def deny_all(as_actor):  # type: ignore[no-untyped-def]
    """A signed-in user with **no** permissions at all."""
    with as_actor(permissions=frozenset()) as session:
        yield session

"""The permission matrix: every service entry point declares a permission.

Hiding a button is not authorisation. This test walks the *real* service
objects, so a new method added without a permission — or one whose permission
is not in the catalogue — fails the build rather than shipping a hole.

REQ-RBAC-001…007, docs/05 §4.
"""

from __future__ import annotations

import inspect
from dataclasses import fields
from typing import Any

import pytest

from dentiva.core.errors import AuthenticationRequired, PermissionDenied
from dentiva.data.seed.roles import ADMIN_ROLE, LOCKOUT_GUARD_PERMISSION, ROLE_TEMPLATES
from dentiva.domain.permissions import BY_CODE, CODES, PERMISSIONS
from dentiva.services import Services
from dentiva.services.audit_service import AuditService
from dentiva.services.rbac import (
    audit_action,
    is_internal,
    is_public_operation,
    required_permission,
    requires_reauthentication,
)

#: Attributes that are part of Python's object protocol, not service entry points.
IGNORED_NAMES = frozenset({"__init__", "__repr__", "__str__"})


def _entry_points(service: Any) -> dict[str, Any]:
    """The callable members of *service* that are part of its public surface."""
    found: dict[str, Any] = {}
    for name, member in vars(type(service)).items():
        if name.startswith("_") and name not in IGNORED_NAMES:
            continue
        if name in IGNORED_NAMES:
            continue
        if not callable(member):
            continue
        found[name] = member
    return found


def _all_services(services: Services) -> dict[str, Any]:
    """Every service instance held by the container (not the session factory)."""
    return {
        field.name: value
        for field in fields(services)
        if type(value := getattr(services, field.name)).__module__.startswith("dentiva.services")
        and _entry_points(value)
    }


# ------------------------------------------------------------------- catalogue --
def test_permission_codes_are_unique_and_well_formed() -> None:
    codes = [spec.code for spec in PERMISSIONS]
    assert len(codes) == len(set(codes)), "duplicate permission code in the catalogue"
    # REQ-RBAC-002: a granular catalogue, not a handful of coarse switches.
    assert len(codes) >= 40, f"the catalogue holds only {len(codes)} permissions"
    for spec in PERMISSIONS:
        assert spec.code == spec.code.strip().lower(), spec.code
        assert spec.label, f"{spec.code} has no label"
        assert spec.description, f"{spec.code} has no description"
        assert spec.group, f"{spec.code} has no group"


def test_financial_permissions_are_a_subset_of_the_catalogue() -> None:
    financial = {spec.code for spec in PERMISSIONS if spec.is_financial}
    assert financial <= set(CODES)
    assert financial, "the catalogue must flag the permissions that expose money"


def test_role_templates_only_use_declared_permissions() -> None:
    from dentiva.domain.rbac import describe

    for template in ROLE_TEMPLATES:
        unknown = sorted(set(template.codes) - set(CODES))
        assert not unknown, f"role '{template.name}' grants unknown codes: {unknown}"
        assert template.codes, f"role '{template.name}' grants nothing at all"
        for code in sorted(template.codes):
            assert describe(code), f"{code} has no human readable label"


def test_administrator_role_grants_every_permission() -> None:
    admin = next(template for template in ROLE_TEMPLATES if template.name == ADMIN_ROLE)
    assert set(admin.codes) == set(CODES)
    assert LOCKOUT_GUARD_PERMISSION in admin.codes


# ---------------------------------------------------------------- the matrix ---
def test_every_service_entry_point_declares_a_permission(services: Services) -> None:
    undeclared: list[str] = []
    for service_name, service in _all_services(services).items():
        if isinstance(service, AuditService):
            # The audit writer joins the caller's transaction; it is not an
            # entry point of its own (every call is already authorised).
            continue
        for method_name, method in _entry_points(service).items():
            if required_permission(method) or is_public_operation(method) or is_internal(method):
                continue
            undeclared.append(f"{service_name}.{method_name}")
    assert not undeclared, (
        "these service methods reach the database without declaring a permission "
        "(add @require, or mark them @public_operation / @internal):\n"
        + "\n".join(sorted(undeclared))
    )


def test_every_declared_permission_exists_in_the_catalogue(services: Services) -> None:
    unknown: list[str] = []
    for service_name, service in _all_services(services).items():
        for method_name, method in _entry_points(service).items():
            permission = required_permission(method)
            if permission is None:
                continue
            if permission not in BY_CODE:
                unknown.append(f"{service_name}.{method_name} -> {permission}")
    assert not unknown, "unknown permission codes:\n" + "\n".join(sorted(unknown))


def test_every_protected_method_records_an_audit_action(services: Services) -> None:
    silent: list[str] = []
    for service_name, service in _all_services(services).items():
        for method_name, method in _entry_points(service).items():
            if required_permission(method) is None:
                continue
            if not audit_action(method):
                silent.append(f"{service_name}.{method_name}")
    assert not silent, "protected methods without an audit action:\n" + "\n".join(sorted(silent))


def test_sensitive_permissions_demand_recent_reauthentication(services: Services) -> None:
    sensitive = {spec.code for spec in PERMISSIONS if spec.sensitive}
    declared = set()
    for service in _all_services(services).values():
        for method in _entry_points(service).values():
            permission = required_permission(method)
            if permission in sensitive:
                assert requires_reauthentication(method), f"{permission} must require re-auth"
                declared.add(permission)
    assert declared, "no service method uses a sensitive permission — the matrix is not wired"


def test_the_matrix_covers_a_realistic_number_of_methods(services: Services) -> None:
    """Guard against the matrix silently going empty (e.g. a refactor)."""
    count = 0
    for service in _all_services(services).values():
        for method in _entry_points(service).values():
            count += 1 if required_permission(method) else 0
    assert count >= 40, f"only {count} protected methods were found"


# ------------------------------------------------------------------ behaviour --
def _required_kwargs(method: Any) -> dict[str, Any]:
    """Dummy values for every keyword-only argument the method needs.

    The permission gate runs *before* the body, so the values are never used —
    they only have to satisfy Python's argument binding.
    """
    parameters = inspect.signature(method).parameters
    return {
        name: None
        for name, parameter in parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
    }


@pytest.mark.usefixtures("deny_all")
def test_a_user_without_permissions_is_refused_every_protected_call(services: Services) -> None:
    failures: list[str] = []
    checked = 0
    for service_name, service in _all_services(services).items():
        for method_name, method in _entry_points(service).items():
            if required_permission(method) is None:
                continue
            checked += 1
            try:
                getattr(service, method_name)(**_required_kwargs(method))
            except PermissionDenied:
                continue
            except Exception as error:
                failures.append(f"{service_name}.{method_name}: {type(error).__name__}: {error}")
            else:
                failures.append(f"{service_name}.{method_name}: no permission required")
    assert not failures, "unprotected service methods:\n" + "\n".join(failures)
    assert checked >= 40


@pytest.mark.usefixtures("deny_all")
def test_denied_attempts_are_written_to_the_audit_log(services: Services) -> None:
    from dentiva.data.session import session_scope

    with pytest.raises(PermissionDenied):
        services.patients.search(term="x")
    with session_scope(services.session_factory) as db:
        page = AuditService().search(db, action="security.denied")
    assert page.total >= 1, "a refused action must be recorded in the audit trail"
    entry = page.items[0]
    assert entry.action == "security.denied"
    assert "patient.view" in (entry.summary or "")


def test_no_session_means_authentication_is_required(services: Services) -> None:
    from dentiva.security.session import set_current

    set_current(None)
    with pytest.raises(AuthenticationRequired):
        services.patients.search(term="x")


def test_sensitive_action_needs_a_fresh_password(services: Services, as_actor) -> None:
    from dentiva.core.errors import ValidationError

    with as_actor(permissions={"user.manage"}) as session:
        with pytest.raises(AuthenticationRequired):
            services.users.create_user(username="newone", password="Dentiva#2026!")
        # After confirming the password the same call proceeds to validation…
        set_current_session(session.grant_reauthentication())
        with pytest.raises(ValidationError):
            services.users.create_user(username="x", password="Dentiva#2026!")


def test_the_administrator_role_cannot_lose_the_guard_permission(
    services: Services,
    admin_session,
) -> None:
    from dentiva.core.errors import ValidationError
    from dentiva.data.models.security import Role
    from dentiva.data.session import session_scope

    with session_scope(services.session_factory) as db:
        admin_role = db.query(Role).filter(Role.name == ADMIN_ROLE).one()
    # Changing roles is sensitive, so the administrator confirms the password first.
    set_current_session(admin_session.grant_reauthentication())
    with pytest.raises(ValidationError):
        services.roles.remove_permission(role_id=admin_role.id, code=LOCKOUT_GUARD_PERMISSION)


def test_roles_resolve_to_the_permissions_they_declare(services: Services, admin_session) -> None:
    with services.session_factory() as db:
        resolved = services.roles.permissions_for(db, admin_session.user_id)
    assert set(CODES) <= set(resolved)


def set_current_session(session) -> None:
    from dentiva.security.session import set_current

    set_current(session)

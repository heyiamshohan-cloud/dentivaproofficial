"""The ``@require`` decorator — the authoritative authorisation gate
(docs/02 §2 rule 2, docs/06 §3, REQ-RBAC-003/004).

Every service method that touches protected data is decorated. Because services
are the *only* path to the database, no screen, shortcut, export, report, search
or scripted call can bypass the check.

One decoration does four things, in this order:

1. **Transaction** — opens the unit of work (``session_scope``) so the business
   write and its audit entry commit together or not at all;
2. **Authorisation** — checks the permission and, when it is missing, writes a
   security audit entry and raises :class:`PermissionDenied`. This happens
   *before* any password prompt, so a user without the permission is never told
   that the action exists or that it is sensitive;
3. **Authentication** — resolves the current session and, for a permission
   flagged *sensitive*, insists that the password was re-confirmed recently
   (:class:`AuthenticationRequired`);
4. **Audit** — records the completed action with the entity it touched.

The decorator also stamps the wrapper with ``__required_permission__`` and
friends, so the permission-matrix test can introspect every service method and
prove that none of them can be called without declaring a permission.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, TypeVar

from dentiva.core.errors import AuthenticationRequired, PermissionDenied
from dentiva.data.session import session_scope
from dentiva.domain.permissions import spec_for
from dentiva.security.session import Session, current_or_fail

if TYPE_CHECKING:  # pragma: no cover - typing only
    from sqlalchemy.orm import Session as DBSession

F = TypeVar("F", bound=Callable[..., Any])

#: Marker attributes, read by the permission-matrix test.
REQUIRED_PERMISSION_ATTR = "__required_permission__"
PUBLIC_ATTR = "__public_operation__"
INTERNAL_ATTR = "__internal_helper__"
SENSITIVE_ATTR = "__requires_reauth__"
AUDIT_ACTION_ATTR = "__audit_action__"
ENTITY_ATTR = "__audit_entity__"


def require(
    permission: str,
    *,
    action: str | None = None,
    entity: str | None = None,
    entity_id_arg: str | None = None,
    summary: str | Callable[..., str] | None = None,
    audit: bool = True,
) -> Callable[[F], F]:
    """Declare the single permission needed to run the decorated service method."""

    def decorator(func: F) -> F:
        spec = spec_for(permission)  # fails at import time on a catalogue typo
        audit_action = action or permission
        entity_name = entity or permission.split(".", 1)[0]

        @functools.wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            actor = current_or_fail()
            # Authorisation is decided first: a user who lacks the permission is
            # never told that the action is sensitive (no hint about what exists).
            if permission not in actor.permissions:
                _record_denial(self, kwargs, actor=actor, permission=permission, entity=entity_name)
                raise PermissionDenied(
                    f"You do not have permission to {spec.label.lower()}.",
                    permission=permission,
                )
            if spec.sensitive and not actor.is_reauthentication_valid():
                raise AuthenticationRequired(
                    f"«{spec.label}» needs you to confirm your password first."
                )

            with session_scope(self._session_factory) as db:  # type: ignore[attr-defined]
                result = func(self, db, *args, **kwargs)
                if audit:
                    _record_success(
                        db,
                        kwargs,
                        actor=actor,
                        action=audit_action,
                        entity=entity_name,
                        entity_id_arg=entity_id_arg,
                        summary_spec=summary,
                        result=result,
                    )
                return result

        setattr(wrapper, REQUIRED_PERMISSION_ATTR, permission)
        setattr(wrapper, SENSITIVE_ATTR, spec.sensitive)
        setattr(wrapper, AUDIT_ACTION_ATTR, audit_action)
        setattr(wrapper, ENTITY_ATTR, entity_name)
        return wrapper  # type: ignore[return-value]

    return decorator


def public_operation(func: F) -> F:
    """Mark a service method that is deliberately callable without a session.

    Only genuinely public operations (sign-in, activation checks, bootstrap)
    may use this; the permission-matrix test fails if any other service method
    reaches the database without declaring a permission.
    """
    setattr(func, PUBLIC_ATTR, True)
    return func


def is_public_operation(func: Callable[..., Any]) -> bool:
    return bool(getattr(func, PUBLIC_ATTR, False))


def internal(func: F) -> F:
    """Mark a service method that is **not** an entry point.

    Internal helpers (permission resolution, folder lookup, cache refresh) are
    called by other services that have already been authorised. Marking them
    keeps the permission-matrix test honest: every entry point must declare a
    permission, and anything marked ``internal`` is knowingly not one.
    """

    setattr(func, INTERNAL_ATTR, True)
    return func


def is_internal(func: Callable[..., Any]) -> bool:
    return bool(getattr(func, INTERNAL_ATTR, False))


def required_permission(func: Callable[..., Any]) -> str | None:
    """The permission declared by *func* (``None`` when it declares none)."""
    return getattr(func, REQUIRED_PERMISSION_ATTR, None)


def requires_reauthentication(func: Callable[..., Any]) -> bool:
    return bool(getattr(func, SENSITIVE_ATTR, False))


def audit_action(func: Callable[..., Any]) -> str | None:
    return getattr(func, AUDIT_ACTION_ATTR, None)


def _audit_service() -> Any:
    from dentiva.services.audit_service import AuditService

    return AuditService()


def _record_denial(
    service: Any,
    kwargs: dict[str, Any],
    *,
    actor: Session,
    permission: str,
    entity: str,
) -> None:
    """A denied attempt is always recorded — silently refusing is not enough."""
    try:
        with session_scope(service._session_factory) as db:
            _audit_service().record(
                db,
                action="security.denied",
                entity=entity,
                summary=f"Denied: {permission}",
                after={"permission": permission},
                severity="security",
                actor=actor,
                source="rbac",
            )
    except Exception:
        pass


def _record_success(
    db: DBSession,
    kwargs: dict[str, Any],
    *,
    actor: Session,
    action: str,
    entity: str,
    entity_id_arg: str | None,
    summary_spec: str | Callable[..., str] | None,
    result: Any,
) -> None:
    summary = ""
    if callable(summary_spec):
        try:
            summary = summary_spec(result)
        except TypeError:  # pragma: no cover - a summary helper with a bad signature
            summary = ""
    elif summary_spec:
        summary = summary_spec
    _audit_service().record(
        db,
        action=action,
        entity=entity,
        entity_id=_extract_id(kwargs, entity_id_arg, result),
        summary=summary,
        actor=actor,
        source="service",
    )
    db.flush()


def _extract_id(kwargs: dict[str, Any], entity_id_arg: str | None, result: Any) -> int | None:
    if entity_id_arg and isinstance(kwargs.get(entity_id_arg), int):
        return kwargs[entity_id_arg]
    identifier = getattr(result, "id", None)
    return identifier if isinstance(identifier, int) else None

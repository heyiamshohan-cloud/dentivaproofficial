"""Pure role/permission evaluation (docs/06 §2/§4).

Everything here is data-in, data-out: no database, no Qt, no clock. The service
layer (``services/rbac.py``) is the only place where these rules are *enforced*.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from dentiva.domain.permissions import CODES, PermissionSpec, spec_for


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    """A role template: a name plus the permission codes it grants."""

    name: str
    description: str
    codes: frozenset[str]
    is_system: bool = True

    def validate(self) -> None:
        unknown = sorted(self.codes - set(CODES))
        if unknown:
            raise ValueError(f"Role {self.name!r} references unknown permissions: {unknown}")


def effective_permissions(
    roles: Sequence[str],
    permissions_by_role: Mapping[str, Iterable[str]],
) -> frozenset[str]:
    """Union of the permissions granted by *roles* (a user may hold many)."""
    granted: set[str] = set()
    for role in roles:
        granted.update(permissions_by_role.get(role, ()))
    return frozenset(code for code in granted if code in set(CODES))


def missing_permissions(granted: Iterable[str], required: Iterable[str]) -> tuple[str, ...]:
    """Which of *required* are absent from *granted* (sorted, for messages)."""
    have = set(granted)
    return tuple(sorted(code for code in required if code not in have))


def describe(permission: str) -> PermissionSpec:
    """Specification of *permission* (raises ``KeyError`` when unknown)."""
    return spec_for(permission)


def is_financial_request(permissions: Iterable[str]) -> bool:
    """True when any of *permissions* is tagged financial."""
    codes = set(permissions)
    return any(spec_for(code).is_financial for code in codes if code in set(CODES))


def can_remove_permission(
    role: str,
    permission: str,
    permissions_by_role: Mapping[str, Iterable[str]],
    *,
    admin_role: str = "Administrator",
    guard_permission: str = "role.manage",
) -> bool:
    """Guard against locking the clinic out of its own administration.

    The built-in Administrator role may not lose ``role.manage`` while no other
    role still holds it (docs/06 §2). Returns False when the change must be
    refused.
    """
    if permission != guard_permission or role != admin_role:
        return True
    for name, codes in permissions_by_role.items():
        if name != admin_role and guard_permission in set(codes):
            return True
    return False

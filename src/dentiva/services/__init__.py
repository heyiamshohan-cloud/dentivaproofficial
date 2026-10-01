"""The Dentiva Pro service layer.

Every business rule lives here, behind :func:`~dentiva.services.rbac.require`.
The UI calls services; it never touches the ORM and never decides who may do
what. One decorated method = one database transaction that carries both the
business write and its audit entry.
"""

from __future__ import annotations

from dentiva.services.container import SERVICE_NAMES, Services
from dentiva.services.rbac import (
    audit_action,
    is_public_operation,
    public_operation,
    require,
    required_permission,
    requires_reauthentication,
)

__all__ = [
    "SERVICE_NAMES",
    "Services",
    "audit_action",
    "is_public_operation",
    "public_operation",
    "require",
    "required_permission",
    "requires_reauthentication",
]

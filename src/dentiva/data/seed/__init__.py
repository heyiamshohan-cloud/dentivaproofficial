"""Default data written once, when a clinic is created (docs/02 §2)."""

from __future__ import annotations

from dentiva.data.seed.catalogs import (
    CLINICAL_CATALOGS,
    DEFAULT_PROFILE_FOR,
    EXPENSE_CATEGORIES,
    MEDICINES,
    PAYMENT_METHODS,
    PRINTER_PROFILES,
    TOOTH_STATUSES,
    TREATMENT_CATEGORIES,
)
from dentiva.data.seed.roles import (
    ADMIN_ROLE,
    LOCKOUT_GUARD_PERMISSION,
    ROLE_TEMPLATE_NAMES,
    ROLE_TEMPLATES,
    template_by_name,
    validate_templates,
)

__all__ = [
    "ADMIN_ROLE",
    "CLINICAL_CATALOGS",
    "DEFAULT_PROFILE_FOR",
    "EXPENSE_CATEGORIES",
    "LOCKOUT_GUARD_PERMISSION",
    "MEDICINES",
    "PAYMENT_METHODS",
    "PRINTER_PROFILES",
    "ROLE_TEMPLATES",
    "ROLE_TEMPLATE_NAMES",
    "TOOTH_STATUSES",
    "TREATMENT_CATEGORIES",
    "template_by_name",
    "validate_templates",
]

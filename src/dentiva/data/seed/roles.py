"""Seeded role templates (docs/06 §2).

Templates are **data**: they are copied into the database at set-up and can then
be edited, cloned or deleted by an administrator. Nothing here is consulted at
runtime for an authorisation decision — the permission table and the user's roles
are.
"""

from __future__ import annotations

from dentiva.domain.permissions import CODES
from dentiva.domain.rbac import RoleDefinition

ALL_PERMISSIONS = frozenset(CODES)

_DENTIST_CLINICAL = frozenset(
    {
        "visit.view",
        "visit.create",
        "visit.edit",
        "chart.view",
        "chart.edit",
        "prescription.view",
        "prescription.create",
        "prescription.edit",
        "prescription.print",
        "treatment.view",
        "treatment.record",
        "referral.view",
        "referral.create",
        "referral.edit",
    }
)

ROLE_TEMPLATES: tuple[RoleDefinition, ...] = (
    RoleDefinition(
        name="Administrator",
        description="Full access, including users, roles, audit, backups and reset.",
        codes=ALL_PERMISSIONS,
    ),
    RoleDefinition(
        name="Dentist",
        description="Clinical work: patients, visits, chart, prescriptions, treatments, referrals.",
        codes=frozenset(
            {
                "patient.view",
                "patient.create",
                "patient.edit",
                "attachment.view",
                "attachment.upload",
                "appointment.view",
                "appointment.create",
                "queue.view",
                "notification.view",
                "clinical_catalog.manage",
            }
        )
        | _DENTIST_CLINICAL,
    ),
    RoleDefinition(
        name="Receptionist",
        description="Front desk: registration, appointments and the queue; read-only money view.",
        codes=frozenset(
            {
                "patient.view",
                "patient.create",
                "patient.edit",
                "attachment.view",
                "attachment.upload",
                "visit.view",
                "appointment.view",
                "appointment.create",
                "appointment.edit",
                "appointment.delete",
                "appointment.complete",
                "queue.view",
                "queue.manage",
                "invoice.view",
                "payment.view",
                "notification.view",
            }
        ),
    ),
    RoleDefinition(
        name="Dental Assistant",
        description="Chairside support: visits, chart viewing, queue and stock usage.",
        codes=frozenset(
            {
                "patient.view",
                "visit.view",
                "visit.create",
                "chart.view",
                "queue.view",
                "queue.manage",
                "inventory.view",
                "inventory.adjust",
                "notification.view",
            }
        ),
    ),
    RoleDefinition(
        name="Accountant",
        description="Invoices, payments, expenses, income and financial reports.",
        codes=frozenset(
            {
                "patient.view",
                "invoice.view",
                "invoice.create",
                "invoice.edit",
                "invoice.print",
                "payment.view",
                "payment.create",
                "payment.edit",
                "payment.void",
                "finance.reports",
                "accounting.view",
                "accounting.manage",
                "finance.export",
                "data.export",
                "notification.view",
            }
        ),
    ),
    RoleDefinition(
        name="Inventory Manager",
        description="Stock, batches, suppliers and purchases.",
        codes=frozenset(
            {
                "patient.view",
                "inventory.view",
                "inventory.manage",
                "inventory.purchase",
                "inventory.adjust",
                "accounting.view",
                "notification.view",
            }
        ),
    ),
    RoleDefinition(
        name="Read-only",
        description="Auditor: read everything they are otherwise permitted to see, change nothing.",
        codes=frozenset(code for code in CODES if code.endswith(".view"))
        | frozenset({"system.health", "notification.view"}),
    ),
)

ROLE_TEMPLATE_NAMES: tuple[str, ...] = tuple(role.name for role in ROLE_TEMPLATES)

ADMIN_ROLE = "Administrator"

#: Guard (docs/06 §2): the Administrator role may not lose ``role.manage``
#: while no other role holds it.
LOCKOUT_GUARD_PERMISSION = "role.manage"


def template_by_name(name: str) -> RoleDefinition:
    for role in ROLE_TEMPLATES:
        if role.name == name:
            return role
    raise KeyError(f"Unknown role template: {name!r}")


def validate_templates() -> None:
    for role in ROLE_TEMPLATES:
        role.validate()

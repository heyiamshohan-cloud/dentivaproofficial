"""The permission catalogue — the single source of truth for authorisation
(docs/06 §1, REQ-RBAC-001/002).

Services declare the permission they need with ``@require("<code>")``; this module
is what is seeded into the ``permission`` table at start-up, so the database can
never drift away from the code.

Flags:
    ``sensitive``    — additionally requires password re-authentication, even for
                       a user who holds the permission.
    ``is_financial`` — touches money; the financial-isolation test suite asserts
                       that no path (service, search, export, report, dashboard)
                       leaks financial data to a user without the tag.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Permission groups, in sidebar order (used for grouping in the role editor).
GROUP_PATIENTS = "patients"
GROUP_CLINICAL = "clinical"
GROUP_SCHEDULING = "scheduling"
GROUP_BILLING = "billing"
GROUP_INVENTORY = "inventory"
GROUP_ADMIN = "administration"
GROUP_DATA = "data"

GROUPS: tuple[str, ...] = (
    GROUP_PATIENTS,
    GROUP_CLINICAL,
    GROUP_SCHEDULING,
    GROUP_BILLING,
    GROUP_INVENTORY,
    GROUP_ADMIN,
    GROUP_DATA,
)


@dataclass(frozen=True, slots=True)
class PermissionSpec:
    """One capability, with the flags that drive enforcement."""

    code: str
    group: str
    label: str
    description: str = ""
    sensitive: bool = False
    is_financial: bool = False


def _spec(
    code: str,
    group: str,
    label: str,
    description: str = "",
    *,
    sensitive: bool = False,
    financial: bool = False,
) -> PermissionSpec:
    return PermissionSpec(code, group, label, description, sensitive, financial)


PERMISSIONS: tuple[PermissionSpec, ...] = (
    # ------------------------------------------------------------- patients --
    _spec("patient.view", GROUP_PATIENTS, "View patients", "Open the patient list and profiles."),
    _spec("patient.create", GROUP_PATIENTS, "Register patients", "Add a new patient record."),
    _spec(
        "patient.edit",
        GROUP_PATIENTS,
        "Edit patients",
        "Change demographics and history (audited).",
    ),
    _spec(
        "patient.archive",
        GROUP_PATIENTS,
        "Archive patients",
        "Deactivate a patient without deleting history.",
    ),
    _spec(
        "patient.delete",
        GROUP_PATIENTS,
        "Delete patients",
        "Hard-delete a patient record.",
        sensitive=True,
    ),
    _spec(
        "patient.merge",
        GROUP_PATIENTS,
        "Merge patients",
        "Merge duplicate patient records.",
        sensitive=True,
    ),
    _spec("patient.export", GROUP_PATIENTS, "Export patients", "Export patient data to CSV/XLSX."),
    _spec("patient.import", GROUP_PATIENTS, "Import patients", "Import patients from a CSV file."),
    _spec("attachment.view", GROUP_PATIENTS, "View attachments", "Open or download an attachment."),
    _spec(
        "attachment.upload",
        GROUP_PATIENTS,
        "Upload attachments",
        "Attach a file to a patient or visit.",
    ),
    _spec(
        "attachment.delete",
        GROUP_PATIENTS,
        "Delete attachments",
        "Remove an attachment.",
        sensitive=True,
    ),
    # ------------------------------------------------------------- clinical --
    _spec("visit.view", GROUP_CLINICAL, "View visits", "Open the visit register and timeline."),
    _spec("visit.create", GROUP_CLINICAL, "Start visits", "Begin a patient visit."),
    _spec("visit.edit", GROUP_CLINICAL, "Edit visits", "Change a visit record (audited)."),
    _spec(
        "visit.delete", GROUP_CLINICAL, "Cancel visits", "Cancel or remove a visit.", sensitive=True
    ),
    _spec("chart.view", GROUP_CLINICAL, "View dental chart", "Open the dental chart."),
    _spec(
        "chart.edit", GROUP_CLINICAL, "Record chart findings", "Record or supersede tooth findings."
    ),
    _spec("prescription.view", GROUP_CLINICAL, "View prescriptions", "Open prescriptions."),
    _spec("prescription.create", GROUP_CLINICAL, "Create prescriptions", "Write a prescription."),
    _spec("prescription.edit", GROUP_CLINICAL, "Edit prescriptions", "Change a prescription."),
    _spec(
        "prescription.delete",
        GROUP_CLINICAL,
        "Delete prescriptions",
        "Void a prescription.",
        sensitive=True,
    ),
    _spec(
        "prescription.print",
        GROUP_CLINICAL,
        "Print prescriptions",
        "Print or export a prescription PDF.",
    ),
    _spec(
        "treatment.view",
        GROUP_CLINICAL,
        "View treatments",
        "Open treatments and the treatment catalog.",
    ),
    _spec(
        "treatment.record",
        GROUP_CLINICAL,
        "Record treatments",
        "Record treatments performed on a visit.",
    ),
    _spec(
        "treatment.manage",
        GROUP_CLINICAL,
        "Manage treatment catalog",
        "Maintain the treatment catalog and prices.",
    ),
    _spec(
        "clinical_catalog.manage",
        GROUP_CLINICAL,
        "Manage clinical catalogs",
        "Maintain complaint, examination and advice lists.",
    ),
    _spec("referral.view", GROUP_CLINICAL, "View referrals", "Open referral records."),
    _spec("referral.create", GROUP_CLINICAL, "Create referrals", "Record a referral out."),
    _spec(
        "referral.edit", GROUP_CLINICAL, "Edit referrals", "Update a referral and its follow-up."
    ),
    # ----------------------------------------------------------- scheduling --
    _spec("appointment.view", GROUP_SCHEDULING, "View appointments", "Open the appointment diary."),
    _spec("appointment.create", GROUP_SCHEDULING, "Create appointments", "Book an appointment."),
    _spec(
        "appointment.edit",
        GROUP_SCHEDULING,
        "Edit appointments",
        "Reschedule or change an appointment.",
    ),
    _spec(
        "appointment.delete",
        GROUP_SCHEDULING,
        "Cancel appointments",
        "Cancel or delete an appointment.",
    ),
    _spec(
        "appointment.complete",
        GROUP_SCHEDULING,
        "Complete appointments",
        "Mark an appointment completed or missed.",
    ),
    _spec("queue.view", GROUP_SCHEDULING, "View queue", "Open the daily queue board."),
    _spec(
        "queue.manage",
        GROUP_SCHEDULING,
        "Manage queue",
        "Call, skip, complete and reorder the queue.",
    ),
    # -------------------------------------------------------------- billing --
    _spec("invoice.view", GROUP_BILLING, "View invoices", "Open invoices.", financial=True),
    _spec("invoice.create", GROUP_BILLING, "Create invoices", "Raise an invoice.", financial=True),
    _spec(
        "invoice.edit",
        GROUP_BILLING,
        "Edit invoices",
        "Change a draft or issued invoice.",
        financial=True,
    ),
    _spec(
        "invoice.void",
        GROUP_BILLING,
        "Void invoices",
        "Void an invoice (reversed, never deleted).",
        sensitive=True,
        financial=True,
    ),
    _spec(
        "invoice.print",
        GROUP_BILLING,
        "Print invoices",
        "Print or export invoices.",
        financial=True,
    ),
    _spec("payment.view", GROUP_BILLING, "View payments", "Open payment history.", financial=True),
    _spec(
        "payment.create",
        GROUP_BILLING,
        "Record payments",
        "Receive a payment against an invoice.",
        financial=True,
    ),
    _spec(
        "payment.edit",
        GROUP_BILLING,
        "Edit payments",
        "Change a payment (audited).",
        sensitive=True,
        financial=True,
    ),
    _spec(
        "payment.void",
        GROUP_BILLING,
        "Void payments",
        "Void or refund a payment.",
        sensitive=True,
        financial=True,
    ),
    _spec(
        "finance.reports",
        GROUP_BILLING,
        "Financial reports",
        "Run financial and accounting reports.",
        financial=True,
    ),
    _spec(
        "accounting.view",
        GROUP_BILLING,
        "View accounting",
        "Open income and expense records.",
        financial=True,
    ),
    _spec(
        "accounting.manage",
        GROUP_BILLING,
        "Manage accounting",
        "Create, edit and delete income and expenses.",
        financial=True,
    ),
    _spec(
        "finance.export",
        GROUP_BILLING,
        "Export financial data",
        "Export financial records.",
        financial=True,
    ),
    # ------------------------------------------------------------ inventory --
    _spec("inventory.view", GROUP_INVENTORY, "View inventory", "Open stock, batches and alerts."),
    _spec(
        "inventory.manage",
        GROUP_INVENTORY,
        "Manage inventory",
        "Maintain items, categories and suppliers.",
    ),
    _spec(
        "inventory.purchase",
        GROUP_INVENTORY,
        "Record purchases",
        "Record a purchase (affects stock and accounting).",
        financial=True,
    ),
    _spec(
        "inventory.adjust", GROUP_INVENTORY, "Adjust stock", "Record usage, damage or corrections."
    ),
    # -------------------------------------------------------- administration --
    _spec("staff.view", GROUP_ADMIN, "View staff", "Open staff records."),
    _spec("staff.manage", GROUP_ADMIN, "Manage staff", "Maintain staff records."),
    _spec("user.view", GROUP_ADMIN, "View users", "Open the user list."),
    _spec(
        "user.manage",
        GROUP_ADMIN,
        "Manage users",
        "Create users, reset passwords, activate and deactivate.",
        sensitive=True,
    ),
    _spec("role.view", GROUP_ADMIN, "View roles", "Open roles and permissions."),
    _spec(
        "role.manage",
        GROUP_ADMIN,
        "Manage roles",
        "Change a role's permissions (audited).",
        sensitive=True,
    ),
    _spec("settings.view", GROUP_ADMIN, "View settings", "Open clinic and system settings."),
    _spec(
        "settings.manage",
        GROUP_ADMIN,
        "Change settings",
        "Change clinic and security settings.",
        sensitive=True,
    ),
    _spec("printer.manage", GROUP_ADMIN, "Manage printing", "Maintain printer and paper profiles."),
    _spec("audit.view", GROUP_ADMIN, "View audit log", "Open the audit log.", sensitive=True),
    _spec(
        "system.health", GROUP_ADMIN, "System health", "Run and read integrity and health reports."
    ),
    _spec(
        "notification.view",
        GROUP_ADMIN,
        "View notifications",
        "See notifications already permitted to you.",
    ),
    # ------------------------------------------------------------ data -------
    _spec("backup.create", GROUP_DATA, "Create backups", "Create and verify a backup."),
    _spec(
        "backup.restore",
        GROUP_DATA,
        "Restore backups",
        "Restore from a backup file.",
        sensitive=True,
    ),
    _spec("data.export", GROUP_DATA, "Export data", "Export any permitted dataset."),
    _spec("data.import", GROUP_DATA, "Import data", "Import data into the clinic."),
    _spec(
        "data.delete",
        GROUP_DATA,
        "Hard-delete records",
        "Permanently delete records.",
        sensitive=True,
    ),
    _spec(
        "business.delete",
        GROUP_DATA,
        "Delete clinic data",
        "Delete a clinic and all of its data.",
        sensitive=True,
    ),
    _spec(
        "app.reset",
        GROUP_DATA,
        "Reset application",
        "Return the application to factory state.",
        sensitive=True,
    ),
)

#: Fast lookup by code.
BY_CODE: dict[str, PermissionSpec] = {spec.code: spec for spec in PERMISSIONS}

#: Every permission code, sorted.
CODES: tuple[str, ...] = tuple(sorted(BY_CODE))

#: Financial permission codes (used by the isolation test matrix).
FINANCIAL_CODES: frozenset[str] = frozenset(spec.code for spec in PERMISSIONS if spec.is_financial)

#: Sensitive permission codes (require re-authentication).
SENSITIVE_CODES: frozenset[str] = frozenset(spec.code for spec in PERMISSIONS if spec.sensitive)


def spec_for(code: str) -> PermissionSpec:
    """Return the specification for *code*; unknown codes are a programming error."""
    try:
        return BY_CODE[code]
    except KeyError as exc:
        raise KeyError(f"Unknown permission code: {code!r}") from exc


def is_financial(code: str) -> bool:
    return code in FINANCIAL_CODES


def is_sensitive(code: str) -> bool:
    return code in SENSITIVE_CODES


def codes_for_group(group: str) -> tuple[str, ...]:
    return tuple(sorted(spec.code for spec in PERMISSIONS if spec.group == group))

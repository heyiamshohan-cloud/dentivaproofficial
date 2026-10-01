"""Navigation model and view registry.

The registry is the single source of truth for the sidebar (REQ-SHL-004). Every
item records the **phase** in which its real screen is delivered; an item whose
phase has not been reached renders :class:`~dentiva.ui.views.pending.ModulePendingView`.

That mechanism is enforced by ``tests/ui/test_navigation_matrix.py``: once
``CURRENT_PHASE`` reaches an item's phase, the test fails until the real screen is
wired in. No placeholder can survive into the release.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from PySide6.QtWidgets import QWidget

#: Phase currently being executed. Advanced at every phase gate.
#: Phase 3 (database, security and the service layer) delivers no screens, so the
#: two administration items that depend on it are scheduled for Phase 13
#: (backup, restore, import/export, data integrity).
CURRENT_PHASE = 3

#: Navigation groups, in the order required by the specification.
PRACTICE = "Practice"
CLINICAL = "Clinical"
BILLING = "Billing"
ADMINISTRATION = "Administration"


@dataclass(frozen=True, slots=True)
class NavItem:
    """A sidebar entry."""

    id: str
    label: str
    icon: str
    group: str
    phase: int
    description: str = ""
    permission: str | None = None
    shortcut: str = ""
    badge: str = ""
    factory: Callable[[], QWidget] | None = field(default=None, compare=False, repr=False)

    @property
    def is_pending(self) -> bool:
        """True while the module is scheduled for a later phase."""
        return self.phase > CURRENT_PHASE or self.factory is None


def _about_view() -> QWidget:
    from dentiva.ui.views.about import AboutView

    return AboutView()


NAV_ITEMS: tuple[NavItem, ...] = (
    # ------------------------------------------------------------ Practice --
    NavItem(
        id="dashboard",
        label="Dashboard",
        icon="dashboard",
        group=PRACTICE,
        phase=12,
        description="Today's patients, appointments, queue, revenue and alerts.",
        shortcut="Ctrl+1",
    ),
    NavItem(
        id="patients",
        label="Patients",
        icon="patients",
        group=PRACTICE,
        phase=6,
        description="Registration, duplicate checks, search and the patient list.",
        permission="patient.view",
        shortcut="Ctrl+2",
    ),
    NavItem(
        id="appointments",
        label="Appointments",
        icon="appointments",
        group=PRACTICE,
        phase=8,
        description="Upcoming and historical appointments with status tracking.",
        permission="appointment.view",
        shortcut="Ctrl+3",
    ),
    NavItem(
        id="queue",
        label="Queue",
        icon="queue",
        group=PRACTICE,
        phase=8,
        description="Live clinic queue: waiting, called, in consultation, completed.",
        permission="queue.view",
        shortcut="Ctrl+4",
    ),
    # ------------------------------------------------------------ Clinical --
    NavItem(
        id="treatments",
        label="Treatments",
        icon="treatments",
        group=CLINICAL,
        phase=7,
        description="Treatment catalogue and the treatments performed register.",
        permission="treatment.view",
        shortcut="Ctrl+5",
    ),
    NavItem(
        id="prescriptions",
        label="Prescriptions",
        icon="prescriptions",
        group=CLINICAL,
        phase=9,
        description="Prescription editor, printing and PDF export.",
        permission="prescription.view",
        shortcut="Ctrl+6",
    ),
    # -------------------------------------------------------------- Billing --
    NavItem(
        id="invoices",
        label="Invoice",
        icon="invoice",
        group=BILLING,
        phase=10,
        description="Invoices with items, discounts, taxes and payment status.",
        permission="invoice.view",
        shortcut="Ctrl+7",
    ),
    NavItem(
        id="payments",
        label="Payments",
        icon="payments",
        group=BILLING,
        phase=10,
        description="Payment ledger with methods, references and daily totals.",
        permission="payment.view",
        shortcut="Ctrl+8",
    ),
    NavItem(
        id="inventory",
        label="Inventory",
        icon="inventory",
        group=BILLING,
        phase=11,
        description="Stock, batches, suppliers, purchases, expiry and low-stock alerts.",
        permission="inventory.view",
    ),
    NavItem(
        id="accounting",
        label="Accounting",
        icon="accounting",
        group=BILLING,
        phase=11,
        description="Income, expenses and period reports.",
        permission="accounting.view",
    ),
    # ------------------------------------------------------- Administration --
    NavItem(
        id="staff_users",
        label="Staff & Users",
        icon="staff",
        group=ADMINISTRATION,
        phase=5,
        description="Staff records, user accounts, roles and permissions.",
        permission="staff.view",
    ),
    NavItem(
        id="backup",
        label="Backup & Restore",
        icon="backup",
        group=ADMINISTRATION,
        phase=13,
        description="Manual and scheduled backups, verification and safe restore.",
        permission="backup.create",
    ),
    NavItem(
        id="settings",
        label="Settings",
        icon="settings",
        group=ADMINISTRATION,
        phase=5,
        description="Clinic, dentists, printing, currency, security and catalogs.",
        permission="settings.view",
        shortcut="Ctrl+,",
    ),
    NavItem(
        id="audit",
        label="Audit Log",
        icon="audit",
        group=ADMINISTRATION,
        phase=13,
        description="Append-only, tamper-evident history of sensitive actions.",
        permission="audit.view",
    ),
    NavItem(
        id="system_health",
        label="System Health",
        icon="health",
        group=ADMINISTRATION,
        phase=13,
        description="Database integrity, audit chain, storage and diagnostics export.",
        permission="system.health",
    ),
    NavItem(
        id="about",
        label="About",
        icon="about",
        group=ADMINISTRATION,
        phase=2,
        description="Product, version, creator and third-party notices.",
        factory=_about_view,
    ),
)

GROUPS: tuple[str, ...] = (PRACTICE, CLINICAL, BILLING, ADMINISTRATION)


def by_id(item_id: str) -> NavItem:
    """Return a navigation item by id."""
    for item in NAV_ITEMS:
        if item.id == item_id:
            return item
    raise KeyError(f"Unknown navigation item: {item_id!r}")


def grouped() -> list[tuple[str, tuple[NavItem, ...]]]:
    """Navigation items grouped and ordered as specified."""
    return [(group, tuple(item for item in NAV_ITEMS if item.group == group)) for group in GROUPS]


def ordered() -> tuple[NavItem, ...]:
    """Flat ordering used by ``Ctrl+1..9`` navigation."""
    return tuple(item for _group, items in grouped() for item in items)


def create_view(item: NavItem) -> QWidget:
    """Instantiate the screen for *item* (pending screen when its phase is ahead)."""
    if item.factory is not None:
        return item.factory()
    from dentiva.ui.views.pending import ModulePendingView

    return ModulePendingView(item)

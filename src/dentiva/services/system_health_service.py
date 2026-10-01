"""System Health: the product's self-check (REQ-SYS-001…006, docs/07 §9).

One screen answers "is my clinic data intact?". It runs, on demand and at
start-up:

* SQLite ``integrity_check`` / ``foreign_key_check``;
* the audit hash chain;
* financial consistency (every invoice's total against its lines and payments,
  and the ``financial_summary`` cache against invoices and payments);
* orphan detection (rows whose parent is gone);
* free disk space and the freshness of the newest verified backup.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import Engine, func, select, text
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core import fileutil
from dentiva.core.clock import local_today, utc_now
from dentiva.core.money import Money
from dentiva.data.engine import check_integrity
from dentiva.data.models.billing import FinancialSummary, Invoice, InvoiceItem, Payment
from dentiva.data.models.patient import Patient
from dentiva.services.audit_service import AuditService
from dentiva.services.rbac import internal, require

#: Minimum free space we are happy to keep working with (256 MiB).
MINIMUM_FREE_BYTES = 256 * 1024 * 1024

#: A backup older than this many days is reported as a warning.
BACKUP_WARNING_DAYS = 7


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One check and what it found."""

    name: str
    ok: bool
    detail: str
    severity: str = "info"  # info | warning | critical

    @property
    def status(self) -> str:
        return "ok" if self.ok else self.severity


@dataclass(frozen=True, slots=True)
class HealthReport:
    """The complete self-check result."""

    checks: tuple[CheckResult, ...] = ()
    checked_at_utc: str = ""
    repair_actions: tuple[str, ...] = ()

    @property
    def healthy(self) -> bool:
        return all(check.ok for check in self.checks)

    @property
    def critical(self) -> tuple[CheckResult, ...]:
        return tuple(
            check for check in self.checks if not check.ok and check.severity == "critical"
        )

    @property
    def warnings(self) -> tuple[CheckResult, ...]:
        return tuple(check for check in self.checks if not check.ok and check.severity == "warning")

    def summary(self) -> str:
        if self.healthy:
            return f"All {len(self.checks)} checks passed."
        return (
            f"{len(self.critical)} critical and {len(self.warnings)} warning(s) "
            f"out of {len(self.checks)} checks."
        )


@dataclass(frozen=True, slots=True)
class FinancialDrift:
    """A single inconsistency between stored and computed money."""

    kind: str
    reference: str
    stored: Money
    computed: Money

    @property
    def difference(self) -> Money:
        return self.computed - self.stored


@dataclass(frozen=True, slots=True)
class FinancialAudit:
    """Result of recomputing the money from its source rows."""

    drift: tuple[FinancialDrift, ...] = field(default=())
    invoices_checked: int = 0
    patients_checked: int = 0

    @property
    def clean(self) -> bool:
        return not self.drift


class SystemHealthService:
    """Run the self-check and repair the derived caches."""

    def __init__(
        self,
        session_factory: sessionmaker[DBSession],
        *,
        engine: Engine | None = None,
        data_directory: str = "",
    ) -> None:
        self._session_factory = session_factory
        self._engine = engine
        self._data_directory = data_directory

    @require("system.health", action="health.check", entity="system")
    def check(self, db: DBSession) -> HealthReport:
        """Run every check and return the report (never raises on findings)."""
        checks: list[CheckResult] = [
            self._database_integrity(db),
            self._audit_chain(db),
            self._financial_consistency(db),
            self._orphans(db),
            self._disk_space(),
            self._backup_freshness(db),
        ]
        return HealthReport(
            checks=tuple(checks),
            checked_at_utc=utc_now().isoformat(),
            repair_actions=tuple(
                check.name for check in checks if not check.ok and check.name == "Financial totals"
            ),
        )

    @require("system.health", action="health.financial_audit", entity="system")
    def financial_audit(self, db: DBSession) -> FinancialAudit:
        """Recompute every invoice and patient total from the source rows."""
        return self._financial_audit(db)

    @require("accounting.manage", action="health.recompute", entity="system")
    def recompute_financial_summary(self, db: DBSession, *, business_id: int) -> int:
        """Rebuild the ``financial_summary`` cache for every patient (audited)."""
        rows = (
            db.execute(select(Patient.id).where(Patient.business_id == business_id)).scalars().all()
        )
        for patient_id in rows:
            self._refresh_summary(db, business_id, int(patient_id))
        db.flush()
        return len(rows)

    @internal
    def backup_status(self, db: DBSession) -> CheckResult:
        """Internal: freshness of the newest verified backup."""
        return self._backup_freshness(db)

    # ---------------------------------------------------------------- internals --
    def _database_integrity(self, db: DBSession) -> CheckResult:
        problems = check_integrity(db.connection())
        return CheckResult(
            name="Database integrity",
            ok=not problems,
            detail="Structure and foreign keys are intact."
            if not problems
            else "; ".join(problems[:3]),
            severity="critical",
        )

    def _audit_chain(self, db: DBSession) -> CheckResult:
        report = AuditService().verify(db)
        return CheckResult(
            name="Audit trail",
            ok=report.intact,
            detail=report.describe(),
            severity="critical",
        )

    def _financial_consistency(self, db: DBSession) -> CheckResult:
        audit = self._financial_audit(db)
        if audit.clean:
            return CheckResult(
                name="Financial totals",
                ok=True,
                detail=(
                    f"{audit.invoices_checked} invoice(s) and {audit.patients_checked} "
                    "patient balance(s) agree with their source rows."
                ),
                severity="critical",
            )
        first = audit.drift[0]
        return CheckResult(
            name="Financial totals",
            ok=False,
            detail=(
                f"{len(audit.drift)} figure(s) disagree with their source rows; "
                f"first: {first.kind} {first.reference} (stored {first.stored}, "
                f"computed {first.computed})."
            ),
            severity="critical",
        )

    def _financial_audit(self, db: DBSession) -> FinancialAudit:
        drift: list[FinancialDrift] = []
        invoices = db.execute(select(Invoice)).scalars().all()
        for invoice in invoices:
            line_total = int(
                db.execute(
                    select(func.coalesce(func.sum(InvoiceItem.line_total_paisa), 0)).where(
                        InvoiceItem.invoice_id == invoice.id
                    )
                ).scalar_one()
                or 0
            )
            expected_total = (
                int(invoice.subtotal_paisa.paisa)
                - int(invoice.discount_paisa.paisa)
                + int(invoice.tax_paisa.paisa)
            )
            if line_total != int(invoice.subtotal_paisa.paisa):
                drift.append(
                    FinancialDrift(
                        kind="invoice subtotal",
                        reference=invoice.number,
                        stored=invoice.subtotal_paisa,
                        computed=Money(line_total),
                    )
                )
            if expected_total != int(invoice.total_paisa.paisa):
                drift.append(
                    FinancialDrift(
                        kind="invoice total",
                        reference=invoice.number,
                        stored=invoice.total_paisa,
                        computed=Money(expected_total),
                    )
                )
            paid = int(
                db.execute(
                    select(func.coalesce(func.sum(Payment.amount_paisa), 0)).where(
                        Payment.invoice_id == invoice.id, Payment.status == "posted"
                    )
                ).scalar_one()
                or 0
            )
            if paid != int(invoice.paid_paisa.paisa):
                drift.append(
                    FinancialDrift(
                        kind="invoice paid",
                        reference=invoice.number,
                        stored=invoice.paid_paisa,
                        computed=Money(paid),
                    )
                )
            if int(invoice.total_paisa.paisa) - paid != int(invoice.due_paisa.paisa):
                drift.append(
                    FinancialDrift(
                        kind="invoice due",
                        reference=invoice.number,
                        stored=invoice.due_paisa,
                        computed=Money(int(invoice.total_paisa.paisa) - paid),
                    )
                )

        summaries = db.execute(select(FinancialSummary)).scalars().all()
        for summary in summaries:
            billed = int(
                db.execute(
                    select(func.coalesce(func.sum(Invoice.total_paisa), 0)).where(
                        Invoice.patient_id == summary.patient_id, Invoice.status != "void"
                    )
                ).scalar_one()
                or 0
            )
            paid = int(
                db.execute(
                    select(func.coalesce(func.sum(Payment.amount_paisa), 0)).where(
                        Payment.patient_id == summary.patient_id, Payment.status == "posted"
                    )
                ).scalar_one()
                or 0
            )
            if billed != int(summary.total_billed_paisa.paisa):
                drift.append(
                    FinancialDrift(
                        kind="patient billed",
                        reference=f"patient #{summary.patient_id}",
                        stored=summary.total_billed_paisa,
                        computed=Money(billed),
                    )
                )
            if paid != int(summary.total_paid_paisa.paisa):
                drift.append(
                    FinancialDrift(
                        kind="patient paid",
                        reference=f"patient #{summary.patient_id}",
                        stored=summary.total_paid_paisa,
                        computed=Money(paid),
                    )
                )
        return FinancialAudit(
            drift=tuple(drift), invoices_checked=len(invoices), patients_checked=len(summaries)
        )

    def _orphans(self, db: DBSession) -> CheckResult:
        counts = {
            name: int(db.execute(text(query)).scalar_one() or 0)
            for name, query in (
                (
                    "payments without an invoice",
                    "SELECT count(*) FROM payment p "
                    "LEFT JOIN invoice i ON i.id = p.invoice_id WHERE i.id IS NULL",
                ),
                (
                    "invoice lines without an invoice",
                    "SELECT count(*) FROM invoice_item l "
                    "LEFT JOIN invoice i ON i.id = l.invoice_id WHERE i.id IS NULL",
                ),
                (
                    "visits without a patient",
                    "SELECT count(*) FROM visit v "
                    "LEFT JOIN patient pt ON pt.id = v.patient_id WHERE pt.id IS NULL",
                ),
                (
                    "stock movements without an item",
                    "SELECT count(*) FROM stock_movement m "
                    "LEFT JOIN inventory_item it ON it.id = m.item_id WHERE it.id IS NULL",
                ),
            )
        }
        total = sum(counts.values())
        detail = (
            "No orphaned rows found."
            if total == 0
            else "; ".join(f"{name}: {count}" for name, count in counts.items() if count)
        )
        return CheckResult(
            name="Orphaned records", ok=total == 0, detail=detail, severity="warning"
        )

    def _disk_space(self) -> CheckResult:
        if not self._data_directory:
            return CheckResult(
                name="Free space",
                ok=True,
                detail="Not checked (no data directory configured).",
                severity="warning",
            )
        free = fileutil.free_space(self._data_directory)
        ok = free >= MINIMUM_FREE_BYTES
        return CheckResult(
            name="Free space",
            ok=ok,
            detail=(
                f"{free / (1024 * 1024):,.0f} MiB free on the data drive."
                if ok
                else f"Only {free / (1024 * 1024):,.0f} MiB free: at least "
                f"{MINIMUM_FREE_BYTES // (1024 * 1024)} MiB is needed for safe operation."
            ),
            severity="warning",
        )

    def _backup_freshness(self, db: DBSession) -> CheckResult:
        from dentiva.data.models.ops import BackupRecord

        row = db.execute(
            select(BackupRecord)
            .where(BackupRecord.status == "complete")
            .order_by(BackupRecord.id.desc())
            .limit(1)
        ).scalar_one_or_none()
        if row is None:
            return CheckResult(
                name="Backup",
                ok=False,
                detail="No backup has been taken yet. Take one before going further.",
                severity="warning",
            )
        age = (local_today() - row.created_at_utc.date()).days
        if not row.verified:
            return CheckResult(
                name="Backup",
                ok=False,
                detail=f"The newest backup ({row.file_name}) failed verification.",
                severity="critical",
            )
        if age > BACKUP_WARNING_DAYS:
            return CheckResult(
                name="Backup",
                ok=False,
                detail=f"The newest verified backup is {age} days old.",
                severity="warning",
            )
        return CheckResult(
            name="Backup",
            ok=True,
            detail=f"Newest verified backup is {age} day(s) old ({row.file_name}).",
            severity="warning",
        )

    def _refresh_summary(self, db: DBSession, business_id: int, patient_id: int) -> None:
        billed = int(
            db.execute(
                select(func.coalesce(func.sum(Invoice.total_paisa), 0)).where(
                    Invoice.patient_id == patient_id, Invoice.status != "void"
                )
            ).scalar_one()
            or 0
        )
        paid = int(
            db.execute(
                select(func.coalesce(func.sum(Payment.amount_paisa), 0)).where(
                    Payment.patient_id == patient_id, Payment.status == "posted"
                )
            ).scalar_one()
            or 0
        )
        last_invoice = db.execute(
            select(func.max(Invoice.issued_at_utc)).where(Invoice.patient_id == patient_id)
        ).scalar_one()
        last_payment = db.execute(
            select(func.max(Payment.paid_at_utc)).where(Payment.patient_id == patient_id)
        ).scalar_one()
        summary = db.execute(
            select(FinancialSummary).where(FinancialSummary.patient_id == patient_id)
        ).scalar_one_or_none()
        if summary is None:
            summary = FinancialSummary(business_id=business_id, patient_id=patient_id)
            db.add(summary)
        summary.total_billed_paisa = Money(billed)
        summary.total_paid_paisa = Money(paid)
        summary.outstanding_paisa = Money(max(0, billed - paid))
        summary.last_invoice_at_utc = last_invoice
        summary.last_payment_at_utc = last_payment
        summary.recomputed_at_utc = utc_now()


def last_backup_date(db: DBSession) -> date | None:
    """The local date of the newest complete backup (dashboard tile)."""
    from dentiva.data.models.ops import BackupRecord

    row = db.execute(
        select(func.max(BackupRecord.created_at_utc)).where(BackupRecord.status == "complete")
    ).scalar_one()
    return row.date() if row else None

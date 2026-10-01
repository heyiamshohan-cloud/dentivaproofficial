"""Global search (docs/07 §1, REQ-SRC-001…004).

One box finds patients, appointments and — **only for users who may see money** —
invoices. The filtering is done here, in the service layer, so a UI that forgets
to hide a column still cannot leak a figure: the financial rows never leave the
service for a user without the financial permission.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.money import Money
from dentiva.data.models.billing import Invoice
from dentiva.data.models.patient import Patient
from dentiva.data.models.scheduling import Appointment
from dentiva.security.session import current
from dentiva.services.rbac import require

#: How many hits per kind are returned (the UI groups them).
MAX_PER_KIND = 12


@dataclass(frozen=True, slots=True)
class PatientHit:
    """A patient match."""

    id: int
    code: str
    name: str
    phone: str
    last_visit_on: date | None


@dataclass(frozen=True, slots=True)
class AppointmentHit:
    """An appointment match."""

    id: int
    patient_name: str
    local_date: date
    start: str
    status: str


@dataclass(frozen=True, slots=True)
class InvoiceHit:
    """An invoice match — only produced for users with ``invoice.view``."""

    id: int
    number: str
    patient_name: str
    local_date: date
    total: Money
    due: Money
    status: str


@dataclass(frozen=True, slots=True)
class SearchResults:
    """What the search box found, already filtered by permission."""

    term: str
    patients: tuple[PatientHit, ...] = ()
    appointments: tuple[AppointmentHit, ...] = ()
    invoices: tuple[InvoiceHit, ...] = ()
    financial_included: bool = False
    omitted_kinds: tuple[str, ...] = field(default=())

    @property
    def is_empty(self) -> bool:
        return not (self.patients or self.appointments or self.invoices)

    @property
    def total(self) -> int:
        return len(self.patients) + len(self.appointments) + len(self.invoices)


class SearchService:
    """The global search box."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    @require("patient.view", action="search.global", entity="search")
    def search(self, db: DBSession, *, term: str, business_id: int) -> SearchResults:
        """Search patients, appointments and (if permitted) invoices."""
        query = (term or "").strip()
        if len(query) < 2:
            return SearchResults(term=query)
        pattern = f"%{query.lower()}%"
        digits = "".join(character for character in query if character.isdigit())

        patient_statement = (
            select(Patient)
            .where(
                Patient.business_id == business_id,
                Patient.deleted_at_utc.is_(None),
                or_(
                    func.lower(Patient.name).like(pattern),
                    func.lower(Patient.code).like(pattern),
                    func.lower(func.coalesce(Patient.name_normalised, "")).like(pattern),
                    *(
                        [func.lower(func.coalesce(Patient.phone_primary, "")).like(f"%{digits}%")]
                        if digits
                        else []
                    ),
                ),
            )
            .order_by(Patient.name)
            .limit(MAX_PER_KIND)
        )
        patients = tuple(
            PatientHit(
                id=row.id,
                code=row.code,
                name=row.name,
                phone=row.phone_primary or "",
                last_visit_on=row.last_visit_on,
            )
            for row in db.execute(patient_statement).scalars().all()
        )

        appointment_statement = (
            select(Appointment)
            .join(Patient, Patient.id == Appointment.patient_id)
            .where(
                Appointment.business_id == business_id,
                or_(
                    func.lower(Patient.name).like(pattern),
                    func.lower(Patient.code).like(pattern),
                    func.lower(func.coalesce(Appointment.reason, "")).like(pattern),
                ),
            )
            .order_by(Appointment.scheduled_start_utc.desc())
            .limit(MAX_PER_KIND)
        )
        appointments: tuple[AppointmentHit, ...] = ()
        if self._has("appointment.view"):
            appointments = tuple(
                AppointmentHit(
                    id=row.id,
                    patient_name=_patient_name(db, row.patient_id),
                    local_date=row.local_date,
                    start=row.scheduled_start_utc.isoformat(),
                    status=row.status,
                )
                for row in db.execute(appointment_statement).scalars().all()
            )

        invoices: tuple[InvoiceHit, ...] = ()
        omitted: list[str] = []
        if self._has("invoice.view"):
            invoice_statement = (
                select(Invoice)
                .join(Patient, Patient.id == Invoice.patient_id)
                .where(
                    Invoice.business_id == business_id,
                    or_(
                        func.lower(Invoice.number).like(pattern),
                        func.lower(Patient.name).like(pattern),
                        func.lower(Patient.code).like(pattern),
                    ),
                )
                .order_by(Invoice.id.desc())
                .limit(MAX_PER_KIND)
            )
            invoices = tuple(
                InvoiceHit(
                    id=row.id,
                    number=row.number,
                    patient_name=_patient_name(db, row.patient_id),
                    local_date=row.local_date,
                    total=row.total_paisa,
                    due=row.due_paisa,
                    status=row.status,
                )
                for row in db.execute(invoice_statement).scalars().all()
            )
        else:
            omitted.append("invoices")

        return SearchResults(
            term=query,
            patients=patients,
            appointments=appointments,
            invoices=invoices,
            financial_included=bool(invoices) or self._has("invoice.view"),
            omitted_kinds=tuple(omitted),
        )

    def _has(self, permission: str) -> bool:
        session = current()
        return bool(session is not None and session.has(permission))


def _patient_name(db: DBSession, patient_id: int) -> str:
    patient = db.get(Patient, patient_id)
    return patient.name if patient else ""

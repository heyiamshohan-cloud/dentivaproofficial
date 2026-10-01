"""Visits: the clinical timeline (docs/04 §3, REQ-VIS-001…008).

A visit is opened once per encounter and never deleted. Notes are **appended**
with a timestamp and the author; correcting a clinical record adds a new entry
rather than rewriting history, and every change is audited.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import local_today, utc_now
from dentiva.core.errors import NotFound, ValidationError
from dentiva.core.money import Money
from dentiva.data.models.clinical import Visit
from dentiva.data.models.patient import Patient
from dentiva.domain.numbering import SCOPE_VISIT, allocate
from dentiva.services.rbac import require

#: Visit lifecycle states.
STATUS_OPEN = "open"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"

ACTIVE_STATUSES = (STATUS_OPEN, STATUS_IN_PROGRESS)
CLOSED_STATUSES = (STATUS_COMPLETED, STATUS_CANCELLED)


@dataclass(frozen=True, slots=True)
class VisitRecord:
    """One visit, as shown in the timeline."""

    id: int
    number: int
    visit_no_display: str
    patient_id: int
    business_id: int
    dentist_id: int | None
    local_date: date
    started_at_utc: str
    ended_at_utc: str | None
    status: str
    reason_for_visit: str
    chief_complaint: str
    clinical_findings: str
    examination_notes: str
    diagnosis: str
    treatment_plan: str
    notes: str
    followup_advice: str
    followup_on: date | None
    version: int
    billed_paisa: int


class VisitService:
    """Open, update and close the clinical encounter."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------ reads --
    @require("visit.view", action="visit.list", entity="patient", entity_id_arg="patient_id")
    def list_for_patient(
        self, db: DBSession, *, patient_id: int, limit: int = 200
    ) -> list[VisitRecord]:
        """Newest-first timeline for one patient."""
        rows = (
            db.execute(
                select(Visit)
                .where(Visit.patient_id == patient_id)
                .order_by(Visit.local_date.desc(), Visit.number.desc())
                .limit(max(1, limit))
            )
            .scalars()
            .all()
        )
        return [self._record(db, row) for row in rows]

    @require("visit.view", action="visit.get", entity="visit", entity_id_arg="visit_id")
    def get(self, db: DBSession, *, visit_id: int) -> VisitRecord:
        """One visit."""
        return self._record(db, self._load(db, visit_id))

    @require("visit.view", action="visit.list", entity="visit")
    def list_for_day(
        self,
        db: DBSession,
        *,
        business_id: int,
        on: date | None = None,
        dentist_id: int | None = None,
        limit: int = 200,
    ) -> list[VisitRecord]:
        """The day's visits (clinician's worklist)."""
        statement = select(Visit).where(
            Visit.business_id == business_id, Visit.local_date == (on or local_today())
        )
        if dentist_id is not None:
            statement = statement.where(Visit.dentist_id == dentist_id)
        rows = db.execute(statement.order_by(Visit.number).limit(max(1, limit))).scalars().all()
        return [self._record(db, row) for row in rows]

    # ----------------------------------------------------------------- writes --
    @require("visit.create", action="visit.start", entity="patient", entity_id_arg="patient_id")
    def start(
        self,
        db: DBSession,
        *,
        patient_id: int,
        business_id: int,
        dentist_id: int | None = None,
        reason_for_visit: str = "",
        appointment_id: int | None = None,
        queue_entry_id: int | None = None,
    ) -> VisitRecord:
        """Open a visit: the patient must exist and be active."""
        patient = db.get(Patient, patient_id)
        if patient is None or patient.deleted_at_utc is not None:
            raise NotFound("That patient record no longer exists.")
        if not patient.is_active:
            raise ValidationError(
                "This patient is archived. Restore the record before a new visit."
            )
        allocated = allocate(db, business_id=business_id, scope=SCOPE_VISIT)
        now = utc_now()
        visit = Visit(
            patient_id=patient_id,
            business_id=business_id,
            number=allocated.number,
            visit_no_display=allocated.value,
            started_at_utc=now,
            local_date=local_today(),
            dentist_id=dentist_id,
            reason_for_visit=(reason_for_visit or "").strip() or None,
            appointment_id=appointment_id,
            queue_entry_id=queue_entry_id,
            status=STATUS_OPEN,
        )
        db.add(visit)
        db.flush()
        patient.last_visit_on = local_today()
        if patient.first_visit_on is None:
            patient.first_visit_on = local_today()
        db.flush()
        return self._record(db, visit)

    @require("visit.edit", action="visit.update", entity="visit", entity_id_arg="visit_id")
    def update(
        self,
        db: DBSession,
        *,
        visit_id: int,
        expected_version: int,
        **changes: object,
    ) -> VisitRecord:
        """Edit the clinical fields of an open or in-progress visit."""
        visit = self._load(db, visit_id)
        if int(visit.version) != int(expected_version):
            raise ValidationError(
                "This visit was changed by someone else. Reload it and apply your edit again."
            )
        if visit.status in CLOSED_STATUSES:
            raise ValidationError("This visit is closed. Reopen it before making changes.")
        allowed = {
            "chief_complaint",
            "clinical_findings",
            "examination_notes",
            "diagnosis",
            "treatment_plan",
            "notes",
            "followup_advice",
            "followup_on",
            "reason_for_visit",
            "dentist_id",
        }
        unknown = sorted(set(changes) - allowed)
        if unknown:
            raise ValidationError(f"These fields cannot be changed here: {', '.join(unknown)}.")
        for field, value in changes.items():
            if field == "followup_on":
                if isinstance(value, str) and value:
                    value = date.fromisoformat(value)
                setattr(visit, field, value)
                continue
            if isinstance(value, str):
                setattr(visit, field, value.strip() or None)
            else:
                setattr(visit, field, value)
        db.flush()
        return self._record(db, visit)

    @require("visit.edit", action="visit.complete", entity="visit", entity_id_arg="visit_id")
    def complete(self, db: DBSession, *, visit_id: int, expected_version: int) -> VisitRecord:
        """Close a visit (it stays readable forever)."""
        visit = self._load(db, visit_id)
        if int(visit.version) != int(expected_version):
            raise ValidationError(
                "This visit was changed by someone else. Reload it and try again."
            )
        if visit.status == STATUS_COMPLETED:
            return self._record(db, visit)
        visit.status = STATUS_COMPLETED
        visit.ended_at_utc = utc_now()
        db.flush()
        return self._record(db, visit)

    @require("visit.delete", action="visit.cancel", entity="visit", entity_id_arg="visit_id")
    def cancel(self, db: DBSession, *, visit_id: int, reason: str) -> VisitRecord:
        """Cancel a visit (sensitive: the row is kept, never destroyed)."""
        visit = self._load(db, visit_id)
        if not (reason or "").strip():
            raise ValidationError("Record why this visit is being cancelled.")
        visit.status = STATUS_CANCELLED
        visit.ended_at_utc = utc_now()
        visit.notes = _append(visit.notes, f"Cancelled: {reason.strip()}")
        db.flush()
        return self._record(db, visit)

    @require("visit.edit", action="visit.reopen", entity="visit", entity_id_arg="visit_id")
    def reopen(self, db: DBSession, *, visit_id: int, reason: str) -> VisitRecord:
        """Reopen a closed visit for a genuine correction (audited)."""
        visit = self._load(db, visit_id)
        if visit.status not in CLOSED_STATUSES:
            return self._record(db, visit)
        if not (reason or "").strip():
            raise ValidationError("Record why this visit is being reopened.")
        visit.status = STATUS_IN_PROGRESS
        visit.ended_at_utc = None
        visit.notes = _append(visit.notes, f"Reopened: {reason.strip()}")
        db.flush()
        return self._record(db, visit)

    # ---------------------------------------------------------------- internals --
    def _load(self, db: DBSession, visit_id: int) -> Visit:
        visit = db.get(Visit, visit_id)
        if visit is None:
            raise NotFound("That visit no longer exists.")
        return visit

    def _billed(self, db: DBSession, visit_id: int) -> Money:
        from dentiva.data.models.billing import Invoice

        total = db.execute(
            select(func.coalesce(func.sum(Invoice.total_paisa), 0)).where(
                Invoice.visit_id == visit_id, Invoice.status != "void"
            )
        ).scalar_one()
        return Money(int(total or 0))

    def _record(self, db: DBSession, visit: Visit) -> VisitRecord:
        return VisitRecord(
            id=visit.id,
            number=visit.number,
            visit_no_display=visit.visit_no_display or f"V-{visit.number:03d}",
            patient_id=visit.patient_id,
            business_id=visit.business_id,
            dentist_id=visit.dentist_id,
            local_date=visit.local_date,
            started_at_utc=visit.started_at_utc.isoformat(),
            ended_at_utc=visit.ended_at_utc.isoformat() if visit.ended_at_utc else None,
            status=visit.status,
            reason_for_visit=visit.reason_for_visit or "",
            chief_complaint=visit.chief_complaint or "",
            clinical_findings=visit.clinical_findings or "",
            examination_notes=visit.examination_notes or "",
            diagnosis=visit.diagnosis or "",
            treatment_plan=visit.treatment_plan or "",
            notes=visit.notes or "",
            followup_advice=visit.followup_advice or "",
            followup_on=visit.followup_on,
            version=int(visit.version),
            billed_paisa=self._billed(db, visit.id).paisa,
        )


def _append(existing: str | None, line: str) -> str:
    stamp = local_today().isoformat()
    return f"{existing}\n[{stamp}] {line}" if existing else f"[{stamp}] {line}"

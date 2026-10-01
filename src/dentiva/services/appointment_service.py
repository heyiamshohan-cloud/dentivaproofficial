"""Appointments and the live queue (docs/04 §4, REQ-APT-001…008, REQ-QUE-001…005).

Status changes are recorded in ``appointment_status_history``, and the queue
enforces one active ticket per patient per day at the database level.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import local_now, local_today, utc_now
from dentiva.core.errors import ConflictError, NotFound, ValidationError
from dentiva.data.models.patient import Patient
from dentiva.data.models.scheduling import Appointment, AppointmentStatusHistory, QueueEntry
from dentiva.domain.numbering import SCOPE_QUEUE_TICKET, allocate
from dentiva.services.rbac import require

#: Appointment states.
STATUS_SCHEDULED = "scheduled"
STATUS_CONFIRMED = "confirmed"
STATUS_ARRIVED = "arrived"
STATUS_IN_CONSULTATION = "in_consultation"
STATUS_COMPLETED = "completed"
STATUS_CANCELLED = "cancelled"
STATUS_NO_SHOW = "no_show"

OPEN_STATUSES = (STATUS_SCHEDULED, STATUS_CONFIRMED, STATUS_ARRIVED, STATUS_IN_CONSULTATION)
TERMINAL_STATUSES = (STATUS_COMPLETED, STATUS_CANCELLED, STATUS_NO_SHOW)

#: Queue states.
QUEUE_WAITING = "waiting"
QUEUE_CALLED = "called"
QUEUE_IN_CONSULTATION = "in_consultation"
QUEUE_COMPLETED = "completed"
QUEUE_SKIPPED = "skipped"
QUEUE_CANCELLED = "cancelled"

LIVE_QUEUE_STATUSES = (QUEUE_WAITING, QUEUE_CALLED, QUEUE_IN_CONSULTATION)

DEFAULT_SLOT_MINUTES = 30


@dataclass(frozen=True, slots=True)
class AppointmentRecord:
    """A booked slot."""

    id: int
    business_id: int
    patient_id: int
    patient_name: str
    patient_code: str
    patient_phone: str
    dentist_id: int | None
    local_date: date
    scheduled_start_utc: str
    scheduled_end_utc: str | None
    duration_minutes: int
    reason: str
    notes: str
    status: str
    visit_id: int | None


@dataclass(frozen=True, slots=True)
class QueueTicket:
    """A live queue entry."""

    id: int
    ticket_number: int
    ticket_display: str
    patient_id: int
    patient_name: str
    patient_code: str
    patient_phone: str
    dentist_id: int | None
    status: str
    priority: int
    appointment_id: int | None
    visit_id: int | None
    called_at_utc: str | None
    started_at_utc: str | None
    notes: str
    waiting_minutes: int


class AppointmentService:
    """Booking, rescheduling, arrival and cancellation."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------ appointments --
    @require("appointment.view", action="appointment.list", entity="appointment")
    def list_for_day(
        self,
        db: DBSession,
        *,
        business_id: int,
        on: date | None = None,
        dentist_id: int | None = None,
        include_cancelled: bool = False,
    ) -> list[AppointmentRecord]:
        """The day book, oldest slot first."""
        statement = select(Appointment).where(
            Appointment.business_id == business_id, Appointment.local_date == (on or local_today())
        )
        if dentist_id is not None:
            statement = statement.where(Appointment.dentist_id == dentist_id)
        if not include_cancelled:
            statement = statement.where(Appointment.status.notin_(TERMINAL_STATUSES))
        rows = (
            db.execute(statement.order_by(Appointment.scheduled_start_utc, Appointment.id))
            .scalars()
            .all()
        )
        return [self._record(db, row) for row in rows]

    @require("appointment.view", action="appointment.search", entity="appointment")
    def search(
        self,
        db: DBSession,
        *,
        business_id: int,
        term: str = "",
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 200,
    ) -> list[AppointmentRecord]:
        """Search appointments by patient name/code/phone within a date range."""
        statement = select(Appointment).where(Appointment.business_id == business_id)
        if from_date:
            statement = statement.where(Appointment.local_date >= from_date)
        if to_date:
            statement = statement.where(Appointment.local_date <= to_date)
        if term := (term or "").strip():
            pattern = f"%{term.lower()}%"
            statement = statement.join(Patient, Patient.id == Appointment.patient_id).where(
                or_(
                    func.lower(Patient.name).like(pattern),
                    func.lower(Patient.code).like(pattern),
                    func.lower(func.coalesce(Patient.phone_primary, "")).like(pattern),
                )
            )
        rows = (
            db.execute(
                statement.order_by(Appointment.scheduled_start_utc.desc()).limit(max(1, limit))
            )
            .scalars()
            .all()
        )
        return [self._record(db, row) for row in rows]

    @require(
        "appointment.view",
        action="appointment.get",
        entity="appointment",
        entity_id_arg="appointment_id",
    )
    def get(self, db: DBSession, *, appointment_id: int) -> AppointmentRecord:
        """One appointment."""
        appointment = db.get(Appointment, appointment_id)
        if appointment is None:
            raise NotFound("That appointment no longer exists.")
        return self._record(db, appointment)

    @require("appointment.create", action="appointment.create", entity="appointment")
    def create(
        self,
        db: DBSession,
        *,
        business_id: int,
        patient_id: int,
        start: datetime,
        dentist_id: int | None = None,
        duration_minutes: int = DEFAULT_SLOT_MINUTES,
        reason: str = "",
        notes: str = "",
    ) -> AppointmentRecord:
        """Book a slot, refusing double-booking of the same dentist."""
        moment = _as_aware(start)
        if duration_minutes < 5 or duration_minutes > 480:
            raise ValidationError("A slot must be between 5 and 480 minutes long.")
        patient = self._patient(db, patient_id)
        if dentist_id is not None:
            end = moment + timedelta(minutes=duration_minutes)
            clash = self._overlap(db, business_id, dentist_id, moment, end)
            if clash is not None:
                raise ConflictError(
                    "The dentist already has an appointment at that time. "
                    f"Conflict with appointment #{clash}."
                )
        appointment = Appointment(
            business_id=business_id,
            patient_id=patient.id,
            dentist_id=dentist_id,
            scheduled_start_utc=moment,
            scheduled_end_utc=moment + timedelta(minutes=duration_minutes),
            local_date=moment.astimezone(local_now().tzinfo).date(),
            duration_minutes=duration_minutes,
            reason=(reason or "").strip() or None,
            notes=(notes or "").strip() or None,
            status=STATUS_SCHEDULED,
        )
        db.add(appointment)
        db.flush()
        db.add(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                from_status=None,
                to_status=STATUS_SCHEDULED,
                changed_at_utc=utc_now(),
                reason="booked",
            )
        )
        db.flush()
        return self._record(db, appointment)

    @require(
        "appointment.edit",
        action="appointment.reschedule",
        entity="appointment",
        entity_id_arg="appointment_id",
    )
    def reschedule(
        self,
        db: DBSession,
        *,
        appointment_id: int,
        start: datetime,
        duration_minutes: int | None = None,
    ) -> AppointmentRecord:
        """Move an appointment (history preserved)."""
        appointment = self._require_open(db, appointment_id)
        moment = _as_aware(start)
        minutes = duration_minutes or appointment.duration_minutes
        if appointment.dentist_id is not None:
            clash = self._overlap(
                db,
                appointment.business_id,
                appointment.dentist_id,
                moment,
                moment + timedelta(minutes=minutes),
                exclude_id=appointment.id,
            )
            if clash is not None:
                raise ConflictError(f"That time is already taken (appointment #{clash}).")
        previous = appointment.status
        appointment.scheduled_start_utc = moment
        appointment.scheduled_end_utc = moment + timedelta(minutes=minutes)
        appointment.duration_minutes = minutes
        appointment.local_date = moment.astimezone(local_now().tzinfo).date()
        db.add(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                from_status=previous,
                to_status=previous,
                changed_at_utc=utc_now(),
                reason="rescheduled",
            )
        )
        db.flush()
        return self._record(db, appointment)

    @require(
        "appointment.edit",
        action="appointment.status",
        entity="appointment",
        entity_id_arg="appointment_id",
    )
    def set_status(
        self,
        db: DBSession,
        *,
        appointment_id: int,
        status: str,
        reason: str = "",
    ) -> AppointmentRecord:
        """Confirm, mark arrived, complete, cancel or mark a no-show."""
        if status not in (
            STATUS_CONFIRMED,
            STATUS_ARRIVED,
            STATUS_COMPLETED,
            STATUS_CANCELLED,
            STATUS_NO_SHOW,
        ):
            raise ValidationError("That appointment status is not recognised.")
        appointment = db.get(Appointment, appointment_id)
        if appointment is None:
            raise NotFound("That appointment no longer exists.")
        if appointment.status == status:
            return self._record(db, appointment)
        if status in (STATUS_CANCELLED, STATUS_NO_SHOW) and not (reason or "").strip():
            raise ValidationError("Record why this appointment is being closed.")
        previous = appointment.status
        appointment.status = status
        db.add(
            AppointmentStatusHistory(
                appointment_id=appointment.id,
                from_status=previous,
                to_status=status,
                changed_at_utc=utc_now(),
                reason=(reason or "").strip() or None,
            )
        )
        db.flush()
        return self._record(db, appointment)

    @require(
        "appointment.delete",
        action="appointment.cancel",
        entity="appointment",
        entity_id_arg="appointment_id",
    )
    def cancel(self, db: DBSession, *, appointment_id: int, reason: str) -> AppointmentRecord:
        """Cancel an appointment (the row and its history are kept)."""
        return self.set_status(
            db, appointment_id=appointment_id, status=STATUS_CANCELLED, reason=reason
        )

    @require(
        "appointment.complete",
        action="appointment.complete",
        entity="appointment",
        entity_id_arg="appointment_id",
    )
    def complete(
        self, db: DBSession, *, appointment_id: int, visit_id: int | None = None
    ) -> AppointmentRecord:
        """Mark the appointment as seen."""
        appointment = db.get(Appointment, appointment_id)
        if appointment is None:
            raise NotFound("That appointment no longer exists.")
        if visit_id is not None:
            appointment.visit_id = visit_id
        return self.set_status(db, appointment_id=appointment_id, status=STATUS_COMPLETED)

    # --------------------------------------------------------------------- queue --
    @require("queue.view", action="queue.list", entity="queue")
    def queue(
        self,
        db: DBSession,
        *,
        business_id: int,
        on: date | None = None,
        include_finished: bool = False,
    ) -> list[QueueTicket]:
        """Today's queue: priority first, then ticket order."""
        statement = select(QueueEntry).where(
            QueueEntry.business_id == business_id,
            QueueEntry.local_date == (on or local_today()),
            QueueEntry.is_deleted.is_(False),
        )
        if not include_finished:
            statement = statement.where(QueueEntry.status.in_(LIVE_QUEUE_STATUSES))
        rows = (
            db.execute(statement.order_by(QueueEntry.priority.desc(), QueueEntry.ticket_number))
            .scalars()
            .all()
        )
        return [self._ticket(db, row) for row in rows]

    @require("queue.manage", action="queue.add", entity="queue")
    def add_to_queue(
        self,
        db: DBSession,
        *,
        business_id: int,
        patient_id: int,
        dentist_id: int | None = None,
        appointment_id: int | None = None,
        priority: int = 0,
        notes: str = "",
    ) -> QueueTicket:
        """Give a patient a ticket (one active ticket per patient per day)."""
        patient = self._patient(db, patient_id)
        day = local_today()
        existing = db.execute(
            select(QueueEntry).where(
                QueueEntry.business_id == business_id,
                QueueEntry.local_date == day,
                QueueEntry.patient_id == patient_id,
                QueueEntry.status.in_(LIVE_QUEUE_STATUSES),
                QueueEntry.is_deleted.is_(False),
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise ConflictError(
                f"{patient.name} is already in today's queue (ticket {existing.ticket_number})."
            )
        allocated = allocate(db, business_id=business_id, scope=SCOPE_QUEUE_TICKET)
        entry = QueueEntry(
            business_id=business_id,
            patient_id=patient.id,
            appointment_id=appointment_id,
            dentist_id=dentist_id,
            ticket_number=allocated.number,
            status=QUEUE_WAITING,
            priority=max(0, priority),
            notes=(notes or "").strip() or None,
            local_date=day,
        )
        db.add(entry)
        db.flush()
        if appointment_id is not None:
            appointment = db.get(Appointment, appointment_id)
            if appointment is not None:
                appointment.queue_entry_id = entry.id
                appointment.status = STATUS_ARRIVED
        db.flush()
        return self._ticket(db, entry)

    @require("queue.manage", action="queue.call", entity="queue", entity_id_arg="entry_id")
    def call_next(
        self,
        db: DBSession,
        *,
        entry_id: int,
        dentist_id: int | None = None,
    ) -> QueueTicket:
        """Call a patient (optionally moving them to another dentist)."""
        entry = self._entry(db, entry_id)
        if entry.status not in (QUEUE_WAITING, QUEUE_CALLED, QUEUE_SKIPPED):
            raise ValidationError(f"This ticket is {entry.status.replace('_', ' ')}.")
        entry.status = QUEUE_CALLED
        entry.called_at_utc = utc_now()
        if dentist_id is not None:
            entry.dentist_id = dentist_id
        db.flush()
        return self._ticket(db, entry)

    @require("queue.manage", action="queue.start", entity="queue", entity_id_arg="entry_id")
    def start_consultation(
        self, db: DBSession, *, entry_id: int, visit_id: int | None = None
    ) -> QueueTicket:
        """Mark the patient as being seen."""
        entry = self._entry(db, entry_id)
        if entry.status not in (QUEUE_WAITING, QUEUE_CALLED, QUEUE_SKIPPED):
            raise ValidationError("Call the patient before starting the consultation.")
        entry.status = QUEUE_IN_CONSULTATION
        entry.started_at_utc = utc_now()
        if visit_id is not None:
            entry.visit_id = visit_id
        db.flush()
        return self._ticket(db, entry)

    @require("queue.manage", action="queue.complete", entity="queue", entity_id_arg="entry_id")
    def complete_queue(self, db: DBSession, *, entry_id: int) -> QueueTicket:
        """Finish a queue entry."""
        entry = self._entry(db, entry_id)
        entry.status = QUEUE_COMPLETED
        entry.completed_at_utc = utc_now()
        db.flush()
        return self._ticket(db, entry)

    @require("queue.manage", action="queue.skip", entity="queue", entity_id_arg="entry_id")
    def skip(self, db: DBSession, *, entry_id: int, reason: str = "") -> QueueTicket:
        """Skip a patient (they stay in the queue)."""
        entry = self._entry(db, entry_id)
        entry.status = QUEUE_SKIPPED
        if reason:
            entry.notes = (entry.notes or "") + f"\nSkipped: {reason.strip()}"
        db.flush()
        return self._ticket(db, entry)

    @require("queue.manage", action="queue.remove", entity="queue", entity_id_arg="entry_id")
    def remove_from_queue(self, db: DBSession, *, entry_id: int, reason: str) -> QueueTicket:
        """Remove a patient from the queue (the row is flagged, not deleted)."""
        entry = self._entry(db, entry_id)
        if not (reason or "").strip():
            raise ValidationError("Record why this patient is being removed from the queue.")
        entry.status = QUEUE_CANCELLED
        entry.is_deleted = True
        entry.notes = (entry.notes or "") + f"\nRemoved: {reason.strip()}"
        db.flush()
        return self._ticket(db, entry)

    @require("queue.manage", action="queue.priority", entity="queue", entity_id_arg="entry_id")
    def set_priority(self, db: DBSession, *, entry_id: int, priority: int) -> QueueTicket:
        """Raise or lower urgency (0 = normal, 1 = urgent, 2 = emergency)."""
        entry = self._entry(db, entry_id)
        if priority not in (0, 1, 2):
            raise ValidationError("Priority must be 0 (normal), 1 (urgent) or 2 (emergency).")
        entry.priority = priority
        db.flush()
        return self._ticket(db, entry)

    @require("queue.view", action="queue.next_ticket", entity="queue")
    def next_ticket_number(self, db: DBSession, *, business_id: int) -> str:
        """Preview of the next ticket, for the reception screen."""
        highest = db.execute(
            select(func.coalesce(func.max(QueueEntry.ticket_number), 0)).where(
                QueueEntry.business_id == business_id, QueueEntry.local_date == local_today()
            )
        ).scalar_one()
        return f"{int(highest) + 1:02d}"

    # ---------------------------------------------------------------- internals --
    def _patient(self, db: DBSession, patient_id: int) -> Patient:
        patient = db.get(Patient, patient_id)
        if patient is None or patient.deleted_at_utc is not None:
            raise NotFound("That patient record no longer exists.")
        return patient

    def _entry(self, db: DBSession, entry_id: int) -> QueueEntry:
        entry = db.get(QueueEntry, entry_id)
        if entry is None:
            raise NotFound("That queue entry no longer exists.")
        return entry

    def _require_open(self, db: DBSession, appointment_id: int) -> Appointment:
        appointment = db.get(Appointment, appointment_id)
        if appointment is None:
            raise NotFound("That appointment no longer exists.")
        if appointment.status in TERMINAL_STATUSES:
            raise ValidationError("That appointment is closed and cannot be changed.")
        return appointment

    def _overlap(
        self,
        db: DBSession,
        business_id: int,
        dentist_id: int,
        start: datetime,
        end: datetime,
        *,
        exclude_id: int | None = None,
    ) -> int | None:
        statement = select(Appointment.id).where(
            Appointment.business_id == business_id,
            Appointment.dentist_id == dentist_id,
            Appointment.status.in_(OPEN_STATUSES),
            Appointment.scheduled_start_utc < end,
            func.coalesce(Appointment.scheduled_end_utc, Appointment.scheduled_start_utc) > start,
        )
        if exclude_id is not None:
            statement = statement.where(Appointment.id != exclude_id)
        return db.execute(statement.limit(1)).scalar_one_or_none()

    def _record(self, db: DBSession, appointment: Appointment) -> AppointmentRecord:
        patient = db.get(Patient, appointment.patient_id)
        return AppointmentRecord(
            id=appointment.id,
            business_id=appointment.business_id,
            patient_id=appointment.patient_id,
            patient_name=patient.name if patient else "",
            patient_code=patient.code if patient else "",
            patient_phone=patient.phone_primary if patient and patient.phone_primary else "",
            dentist_id=appointment.dentist_id,
            local_date=appointment.local_date,
            scheduled_start_utc=appointment.scheduled_start_utc.isoformat(),
            scheduled_end_utc=appointment.scheduled_end_utc.isoformat()
            if appointment.scheduled_end_utc
            else None,
            duration_minutes=appointment.duration_minutes,
            reason=appointment.reason or "",
            notes=appointment.notes or "",
            status=appointment.status,
            visit_id=appointment.visit_id,
        )

    def _ticket(self, db: DBSession, entry: QueueEntry) -> QueueTicket:
        patient = db.get(Patient, entry.patient_id)
        waiting = 0
        if entry.status in LIVE_QUEUE_STATUSES and entry.created_at_utc:
            waiting = max(0, int((utc_now() - entry.created_at_utc).total_seconds() // 60))
        return QueueTicket(
            id=entry.id,
            ticket_number=entry.ticket_number,
            ticket_display=f"{entry.ticket_number:02d}",
            patient_id=entry.patient_id,
            patient_name=patient.name if patient else "",
            patient_code=patient.code if patient else "",
            patient_phone=patient.phone_primary if patient and patient.phone_primary else "",
            dentist_id=entry.dentist_id,
            status=entry.status,
            priority=entry.priority,
            appointment_id=entry.appointment_id,
            visit_id=entry.visit_id,
            called_at_utc=entry.called_at_utc.isoformat() if entry.called_at_utc else None,
            started_at_utc=entry.started_at_utc.isoformat() if entry.started_at_utc else None,
            notes=entry.notes or "",
            waiting_minutes=waiting,
        )


def _as_aware(moment: datetime) -> datetime:
    """Accept a naive datetime as local time, per the clinic's timezone."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=local_now().tzinfo)
    return moment

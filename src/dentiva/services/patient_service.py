"""Patient master records (docs/04 §2, docs/07 §2, REQ-PAT-001…012).

Rules enforced here, not in the UI:

* a patient is **archived**, never silently deleted;
* a hard delete is a separate, sensitive, re-authenticated operation that is
  refused when financial documents still reference the patient;
* every search is bounded and returns a stable order, so the grid never blocks
  the UI thread on an unbounded scan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import local_today, utc_now
from dentiva.core.errors import ConfirmationRequired, ConflictError, NotFound, ValidationError
from dentiva.data.models.billing import Invoice
from dentiva.data.models.patient import Patient
from dentiva.domain.numbering import SCOPE_PATIENT, allocate, peek
from dentiva.services.rbac import require

#: Hard-delete confirmation phrase; the UI must make the user type it exactly.
DELETE_PHRASE = "DELETE"

#: Upper bound on rows returned by one screen (display only — the database has
#: no artificial cap, we simply never load it all into memory).
PAGE_SIZE = 200

_PHONE_DIGITS = re.compile(r"\D+")


@dataclass(frozen=True, slots=True)
class PatientSummary:
    """One row of the patient list."""

    id: int
    code: str
    name: str
    phone: str
    age_display: str
    gender: str
    last_visit_on: date | None
    is_active: bool


@dataclass(frozen=True, slots=True)
class PatientRecord:
    """A full patient record for the detail screen."""

    id: int
    business_id: int
    code: str
    name: str
    guardian_name: str
    relation_of_guardian: str
    dob: date | None
    age_display: str
    gender: str
    blood_group: str
    marital_status: str
    occupation: str
    nid_or_passport: str
    address_line1: str
    address_line2: str
    city: str
    district: str
    postal_code: str
    country: str
    phone_primary: str
    phone_secondary: str
    emergency_contact_name: str
    emergency_contact_phone: str
    email: str
    preferred_language: str
    referred_by: str
    presenting_complaint: str
    past_medical_history: str
    past_dental_history: str
    allergies: str
    current_medication: str
    habits: str
    notes: str
    tags: str
    is_active: bool
    first_visit_on: date | None
    last_visit_on: date | None
    registered_at_utc: str
    version: int


class PatientService:
    """Registration, editing, archiving and retrieval of patients."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    # ------------------------------------------------------------------ reads --
    @require("patient.view", action="patient.list", entity="patient")
    def search(
        self,
        db: DBSession,
        *,
        term: str = "",
        include_archived: bool = False,
        limit: int = PAGE_SIZE,
        offset: int = 0,
    ) -> list[PatientSummary]:
        """Search by name, code, phone or national id (bounded, ordered)."""
        statement = self._search_statement(term, include_archived).limit(
            max(1, min(limit, PAGE_SIZE))
        )
        if offset:
            statement = statement.offset(offset)
        return [self._summarise(row) for row in db.execute(statement).scalars().all()]

    @require("patient.view", action="patient.count", entity="patient")
    def count(self, db: DBSession, *, term: str = "", include_archived: bool = False) -> int:
        """How many patients match — drives the pager without loading rows."""
        statement = select(func.count()).select_from(
            self._search_statement(term, include_archived).subquery()
        )
        return int(db.execute(statement).scalar_one())

    @require("patient.view", action="patient.get", entity="patient", entity_id_arg="patient_id")
    def get(self, db: DBSession, *, patient_id: int) -> PatientRecord:
        """Load one patient record."""
        return self._record(self._load(db, patient_id))

    @require(
        "patient.view", action="patient.duplicates", entity="patient", entity_id_arg="patient_id"
    )
    def duplicate_candidates(self, db: DBSession, *, patient_id: int) -> list[PatientSummary]:
        """Possible duplicates by normalised name plus phone (REQ-PAT-011)."""
        patient = self._load(db, patient_id)
        statement = (
            select(Patient)
            .where(
                Patient.business_id == patient.business_id,
                Patient.id != patient.id,
                Patient.deleted_at_utc.is_(None),
                or_(
                    (Patient.name_normalised == patient.name_normalised)
                    & (patient.name_normalised != ""),
                    (Patient.phone_primary == patient.phone_primary)
                    & Patient.phone_primary.is_not(None),
                ),
            )
            .order_by(Patient.name)
            .limit(20)
        )
        return [self._summarise(row) for row in db.execute(statement).scalars().all()]

    @require("patient.create", action="patient.code.peek", entity="patient")
    def next_code(self, db: DBSession, *, business_id: int) -> str:
        """Preview of the next patient code, for the registration form."""
        return peek(db, business_id=business_id, scope=SCOPE_PATIENT)

    # ----------------------------------------------------------------- writes --
    @require("patient.create", action="patient.register", entity="patient")
    def register(
        self,
        db: DBSession,
        *,
        business_id: int,
        name: str,
        phone_primary: str = "",
        guardian_name: str = "",
        relation_of_guardian: str = "",
        dob: date | None = None,
        gender: str = "",
        address_line1: str = "",
        city: str = "",
        notes: str = "",
        allergies: str = "",
    ) -> PatientRecord:
        """Register a patient, allocating the next code atomically."""
        clean = (name or "").strip()
        if not clean:
            raise ValidationError("Enter the patient's name.")
        phone = normalise_phone(phone_primary)
        if phone_primary and not phone:
            raise ValidationError("That phone number has no digits.")
        if phone and self._phone_taken(db, business_id, phone):
            raise ConflictError(
                f"Another patient already uses {phone}. Check the duplicate list before continuing."
            )
        allocated = allocate(db, business_id=business_id, scope=SCOPE_PATIENT)
        patient = Patient(
            business_id=business_id,
            code=allocated.value,
            name=clean,
            name_normalised=normalise_name(clean),
            guardian_name=(guardian_name or "").strip() or None,
            relation_of_guardian=(relation_of_guardian or "").strip() or None,
            dob=dob,
            age_years_cached=age_from_dob(dob),
            age_updated_on=local_today(),
            gender=(gender or "").strip() or None,
            address_line1=(address_line1 or "").strip() or None,
            city=(city or "").strip() or None,
            phone_primary=phone or None,
            notes=(notes or "").strip() or None,
            allergies=(allergies or "").strip() or None,
            registered_at_utc=utc_now(),
            is_active=True,
        )
        db.add(patient)
        db.flush()
        return self._record(patient)

    @require("patient.edit", action="patient.update", entity="patient", entity_id_arg="patient_id")
    def update(
        self,
        db: DBSession,
        *,
        patient_id: int,
        expected_version: int,
        **changes: object,
    ) -> PatientRecord:
        """Apply validated changes to a patient (optimistic locking)."""
        patient = self._load(db, patient_id)
        if int(patient.version) != int(expected_version):
            raise ConflictError(
                "This record was changed by someone else. Reload it and apply your edit again."
            )
        allowed = {
            "name",
            "guardian_name",
            "relation_of_guardian",
            "dob",
            "gender",
            "blood_group",
            "marital_status",
            "occupation",
            "nid_or_passport",
            "address_line1",
            "address_line2",
            "city",
            "district",
            "postal_code",
            "country",
            "phone_primary",
            "phone_secondary",
            "emergency_contact_name",
            "emergency_contact_phone",
            "email",
            "preferred_language",
            "referred_by",
            "presenting_complaint",
            "past_medical_history",
            "past_dental_history",
            "allergies",
            "current_medication",
            "habits",
            "notes",
            "tags",
        }
        unknown = sorted(set(changes) - allowed)
        if unknown:
            raise ValidationError(f"These fields cannot be changed here: {', '.join(unknown)}.")
        if "phone_primary" in changes:
            phone = normalise_phone(str(changes["phone_primary"] or ""))
            if changes["phone_primary"] and not phone:
                raise ValidationError("That phone number has no digits.")
            if phone and self._phone_taken(db, patient.business_id, phone, exclude_id=patient.id):
                raise ConflictError(f"Another patient already uses {phone}.")
            changes["phone_primary"] = phone or None
        for field, value in changes.items():
            if field == "name":
                text = str(value or "").strip()
                if not text:
                    raise ValidationError("Enter the patient's name.")
                patient.name = text
                patient.name_normalised = normalise_name(text)
                continue
            if field == "dob":
                value = _as_date(value)
                patient.dob = value
                patient.age_years_cached = age_from_dob(value)
                patient.age_updated_on = local_today()
                continue
            if isinstance(value, str):
                setattr(patient, field, value.strip() or None)
            else:
                setattr(patient, field, value)
        patient.updated_at_utc = utc_now()
        db.flush()
        return self._record(patient)

    @require(
        "patient.archive", action="patient.archive", entity="patient", entity_id_arg="patient_id"
    )
    def archive(self, db: DBSession, *, patient_id: int, reason: str = "") -> PatientRecord:
        """Archive a patient: the record and its history stay intact."""
        patient = self._load(db, patient_id)
        if not patient.is_active:
            return self._record(patient)
        patient.is_active = False
        patient.notes = _append_note(
            patient.notes, f"Archived: {(reason or '').strip() or 'no reason given'}"
        )
        patient.updated_at_utc = utc_now()
        db.flush()
        return self._record(patient)

    @require(
        "patient.archive", action="patient.restore", entity="patient", entity_id_arg="patient_id"
    )
    def restore(self, db: DBSession, *, patient_id: int) -> PatientRecord:
        """Bring an archived patient back into the active list."""
        patient = self._load(db, patient_id)
        patient.is_active = True
        patient.deleted_at_utc = None
        patient.updated_at_utc = utc_now()
        db.flush()
        return self._record(patient)

    @require(
        "patient.delete", action="patient.delete", entity="patient", entity_id_arg="patient_id"
    )
    def hard_delete(
        self,
        db: DBSession,
        *,
        patient_id: int,
        confirmation_phrase: str,
    ) -> None:
        """Permanently remove a patient (sensitive; refuses financial traces).

        The permission is sensitive, so the caller must have re-entered the
        password within the last few minutes, and the action is audited.
        """
        if confirmation_phrase.strip().upper() != DELETE_PHRASE:
            raise ConfirmationRequired(
                "Type DELETE to permanently remove this patient and every "
                "clinical record attached.",
                action="patient.delete",
                phrase=DELETE_PHRASE,
            )
        patient = self._load(db, patient_id)
        invoices = int(
            db.execute(
                select(func.count(Invoice.id)).where(Invoice.patient_id == patient_id)
            ).scalar_one()
        )
        if invoices:
            raise ValidationError(
                "This patient has invoices, so the record must be kept for the accounts. "
                "Archive the patient instead."
            )
        db.delete(patient)
        db.flush()

    # ---------------------------------------------------------------- internals --
    def _load(self, db: DBSession, patient_id: int) -> Patient:
        patient = db.get(Patient, patient_id)
        if patient is None or patient.deleted_at_utc is not None:
            raise NotFound("That patient record no longer exists.")
        return patient

    def _search_statement(self, term: str, include_archived: bool) -> Select[Patient]:
        statement = select(Patient).where(Patient.deleted_at_utc.is_(None))
        if not include_archived:
            statement = statement.where(Patient.is_active.is_(True))
        if search := (term or "").strip():
            like = f"%{search.lower()}%"
            digits = _PHONE_DIGITS.sub("", search)
            conditions = [
                func.lower(Patient.name).like(like),
                func.lower(Patient.code).like(like),
                func.lower(func.coalesce(Patient.name_normalised, "")).like(like),
            ]
            if digits:
                conditions.append(func.replace(Patient.phone_primary, "-", "").like(f"%{digits}%"))
            statement = statement.where(or_(*conditions))
        return statement.order_by(Patient.name_normalised, Patient.id)

    def _phone_taken(
        self,
        db: DBSession,
        business_id: int,
        phone: str,
        *,
        exclude_id: int | None = None,
    ) -> bool:
        statement = select(Patient.id).where(
            Patient.business_id == business_id,
            Patient.phone_primary == phone,
            Patient.deleted_at_utc.is_(None),
        )
        if exclude_id is not None:
            statement = statement.where(Patient.id != exclude_id)
        return db.execute(statement).scalar_one_or_none() is not None

    def _summarise(self, patient: Patient) -> PatientSummary:
        return PatientSummary(
            id=patient.id,
            code=patient.code,
            name=patient.name,
            phone=patient.phone_primary or "",
            age_display=format_age(patient.dob, patient.age_years_cached),
            gender=patient.gender or "",
            last_visit_on=patient.last_visit_on,
            is_active=bool(patient.is_active),
        )

    def _record(self, patient: Patient) -> PatientRecord:
        return PatientRecord(
            id=patient.id,
            business_id=patient.business_id,
            code=patient.code,
            name=patient.name,
            guardian_name=patient.guardian_name or "",
            relation_of_guardian=patient.relation_of_guardian or "",
            dob=patient.dob,
            age_display=format_age(patient.dob, patient.age_years_cached),
            gender=patient.gender or "",
            blood_group=patient.blood_group or "",
            marital_status=patient.marital_status or "",
            occupation=patient.occupation or "",
            nid_or_passport=patient.nid_or_passport or "",
            address_line1=patient.address_line1 or "",
            address_line2=patient.address_line2 or "",
            city=patient.city or "",
            district=patient.district or "",
            postal_code=patient.postal_code or "",
            country=patient.country or "",
            phone_primary=patient.phone_primary or "",
            phone_secondary=patient.phone_secondary or "",
            emergency_contact_name=patient.emergency_contact_name or "",
            emergency_contact_phone=patient.emergency_contact_phone or "",
            email=patient.email or "",
            preferred_language=patient.preferred_language or "bn",
            referred_by=patient.referred_by or "",
            presenting_complaint=patient.presenting_complaint or "",
            past_medical_history=patient.past_medical_history or "",
            past_dental_history=patient.past_dental_history or "",
            allergies=patient.allergies or "",
            current_medication=patient.current_medication or "",
            habits=patient.habits or "",
            notes=patient.notes or "",
            tags=patient.tags or "",
            is_active=bool(patient.is_active),
            first_visit_on=patient.first_visit_on,
            last_visit_on=patient.last_visit_on,
            registered_at_utc=patient.registered_at_utc.isoformat(),
            version=int(patient.version),
        )


def normalise_phone(value: str) -> str:
    """Strip formatting, keeping a Bangladeshi number comparable (REQ-PAT-004)."""
    digits = _PHONE_DIGITS.sub("", value or "")
    if digits.startswith("880") and len(digits) > 11:
        digits = digits[3:]
    if digits.startswith("0"):
        digits = digits.lstrip("0")
    return digits


def normalise_name(value: str) -> str:
    """Case- and space-insensitive key used for duplicate detection."""
    return " ".join((value or "").lower().split())


def age_from_dob(dob: date | None) -> int | None:
    """Whole years between *dob* and today, or ``None`` when unknown."""
    if dob is None:
        return None
    today = local_today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(0, years)


def format_age(dob: date | None, cached: int | None = None) -> str:
    """Display age as ``34y`` / ``7m`` / ``12d`` (infants in months or days)."""
    if dob is None:
        return f"{cached}y" if cached is not None else "—"
    today = local_today()
    days = (today - dob).days
    if days < 0:
        return "—"
    if days < 31:
        return f"{days}d"
    if days < 365:
        return f"{days // 30}m"
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return f"{years}y"


def _as_date(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        return date.fromisoformat(value)
    raise ValidationError("That date is not valid.")


def _append_note(existing: str | None, addition: str) -> str:
    stamp = local_today().isoformat()
    line = f"[{stamp}] {addition}"
    return f"{existing}\n{line}" if existing else line

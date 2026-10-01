"""Clinical records: visits, chart, treatments, prescriptions (docs/04 §3).

History rule (REQ-MED-002): findings and clinical rows are **insert-only**. The
"current" chart is a projection over the latest non-superseded finding per tooth,
and "as of visit V" is the projection over findings with ``visit_id <= V``.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.core.money import Money
from dentiva.data.base import AuditColumns, Base, SoftDeleteColumns, VersionedColumns


class ClinicalCatalog(AuditColumns, Base):
    """Clinic-maintained lists: complaints, examinations, advice, diagnoses."""

    __tablename__ = "clinical_catalog"
    __table_args__ = (
        Index(
            "uq_clinical_catalog_business_id_kind_code", "business_id", "kind", "code", unique=True
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Visit(AuditColumns, VersionedColumns, Base):
    """One patient encounter — the spine of the clinical timeline."""

    __tablename__ = "visit"
    __table_args__ = (
        Index("uq_visit_patient_id_number", "patient_id", "number", unique=True),
        Index("ix_visit_patient_id_started_at_utc", "patient_id", "started_at_utc"),
        Index("ix_visit_business_id_local_date", "business_id", "local_date"),
        Index("ix_visit_dentist_id_local_date", "dentist_id", "local_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    visit_no_display: Mapped[str | None] = mapped_column(String(40), nullable=True)
    started_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    ended_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    assisted_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    reason_for_visit: Mapped[str | None] = mapped_column(Text, nullable=True)
    chief_complaint: Mapped[str | None] = mapped_column(Text, nullable=True)
    clinical_findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    examination_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    treatment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    followup_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    followup_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    queue_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("queue_entry.id", ondelete="SET NULL"), nullable=True
    )
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointment.id", ondelete="SET NULL"), nullable=True
    )
    invoice_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoice.id", ondelete="SET NULL"), nullable=True
    )
    next_appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointment.id", ondelete="SET NULL"), nullable=True
    )


class VisitComplaint(Base):
    """Catalogued complaint recorded on a visit (free text always allowed)."""

    __tablename__ = "visit_complaint"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(
        ForeignKey("visit.id", ondelete="CASCADE"), nullable=False, index=True
    )
    catalog_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("clinical_catalog.id", ondelete="SET NULL"), nullable=True
    )
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class VisitExamination(Base):
    """Catalogued examination finding recorded on a visit."""

    __tablename__ = "visit_examination"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_id: Mapped[int] = mapped_column(
        ForeignKey("visit.id", ondelete="CASCADE"), nullable=False, index=True
    )
    catalog_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("clinical_catalog.id", ondelete="SET NULL"), nullable=True
    )
    free_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class ToothStatusCatalog(Base):
    """Visual vocabulary for the dental chart (adult + paediatric)."""

    __tablename__ = "tooth_status_catalog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(40), nullable=False, unique=True)
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    color_token: Mapped[str] = mapped_column(String(40), nullable=False, default="neutral")
    shape: Mapped[str] = mapped_column(String(24), nullable=False, default="fill")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class DentalChart(AuditColumns, Base):
    """A chart version. ``visit_id IS NULL`` means the live/current chart."""

    __tablename__ = "dental_chart"
    __table_args__ = (Index("ix_dental_chart_patient_id_visit_id", "patient_id", "visit_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, index=True
    )
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    dentition: Mapped[str] = mapped_column(String(16), nullable=False, default="adult")
    recorded_by_dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    recorded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ToothFinding(Base):
    """Insert-only tooth finding. Superseding never edits the old row."""

    __tablename__ = "tooth_finding"
    __table_args__ = (Index("ix_tooth_finding_chart_id_tooth_fdi", "chart_id", "tooth_fdi"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chart_id: Mapped[int] = mapped_column(
        ForeignKey("dental_chart.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tooth_fdi: Mapped[str] = mapped_column(String(3), nullable=False)
    surfaces: Mapped[str | None] = mapped_column(String(24), nullable=True)
    status_id: Mapped[int | None] = mapped_column(
        ForeignKey("tooth_status_catalog.id", ondelete="RESTRICT"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    recorded_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    recorded_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    superseded_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)


class TreatmentCategory(Base):
    """Grouping for the treatment catalog."""

    __tablename__ = "treatment_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class TreatmentCatalog(AuditColumns, SoftDeleteColumns, Base):
    """Priced treatment catalogue. Retiring an item never rewrites history."""

    __tablename__ = "treatment_catalog"
    __table_args__ = (
        Index("uq_treatment_catalog_business_id_code", "business_id", "code", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("treatment_category.id", ondelete="SET NULL"), nullable=True
    )
    default_price_paisa: Mapped[Money] = mapped_column(nullable=False, default=Money.zero)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TreatmentRecord(AuditColumns, Base):
    """A treatment *performed*, with catalog snapshots frozen at that moment."""

    __tablename__ = "treatment_record"
    __table_args__ = (Index("ix_treatment_record_visit_id", "visit_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="CASCADE"), nullable=True
    )
    dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    treatment_catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("treatment_catalog.id", ondelete="SET NULL"), nullable=True
    )
    name_snapshot: Mapped[str] = mapped_column(String(200), nullable=False)
    category_snapshot: Mapped[str | None] = mapped_column(String(120), nullable=True)
    price_snapshot_paisa: Mapped[Money | None] = mapped_column(nullable=True)
    tooth_fdi: Mapped[str | None] = mapped_column(String(3), nullable=True)
    surfaces: Mapped[str | None] = mapped_column(String(24), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="completed")
    performed_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    invoice_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("invoice_item.id", ondelete="SET NULL"), nullable=True
    )


class MedicineCatalog(AuditColumns, Base):
    """Autocomplete source for prescriptions. Free text is always allowed."""

    __tablename__ = "medicine_catalog"
    __table_args__ = (
        Index(
            "uq_medicine_catalog_business_id_name_form_strength",
            "business_id",
            "name",
            "form",
            "strength",
            unique=True,
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int | None] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    form: Mapped[str | None] = mapped_column(String(40), nullable=True)
    strength: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Prescription(AuditColumns, VersionedColumns, Base):
    """A prescription document. Voiding never destroys the row (REQ-MED-001)."""

    __tablename__ = "prescription"
    __table_args__ = (
        Index(
            "uq_prescription_business_id_document_number",
            "business_id",
            "document_number",
            unique=True,
        ),
        Index("ix_prescription_patient_id_prescribed_at_utc", "patient_id", "prescribed_at_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    prescribed_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    cc: Mapped[str | None] = mapped_column(Text, nullable=True)
    oe: Mapped[str | None] = mapped_column(Text, nullable=True)
    re_or_advice: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_review_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    template_profile: Mapped[str] = mapped_column(String(40), nullable=False, default="full")
    document_number: Mapped[str] = mapped_column(String(40), nullable=False)
    is_printed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    printed_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    voided_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    voided_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    void_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class PrescriptionItem(Base):
    """One medicine line: structured dose/frequency/duration plus free text."""

    __tablename__ = "prescription_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("prescription.id", ondelete="CASCADE"), nullable=False, index=True
    )
    medicine_catalog_id: Mapped[int | None] = mapped_column(
        ForeignKey("medicine_catalog.id", ondelete="SET NULL"), nullable=True
    )
    medicine_name: Mapped[str] = mapped_column(String(200), nullable=False)
    form: Mapped[str | None] = mapped_column(String(40), nullable=True)
    strength: Mapped[str | None] = mapped_column(String(80), nullable=True)
    dose: Mapped[str | None] = mapped_column(String(80), nullable=True)
    frequency_code: Mapped[str | None] = mapped_column(String(24), nullable=True)
    morning: Mapped[str | None] = mapped_column(String(16), nullable=True)
    noon: Mapped[str | None] = mapped_column(String(16), nullable=True)
    night: Mapped[str | None] = mapped_column(String(16), nullable=True)
    other: Mapped[str | None] = mapped_column(String(16), nullable=True)
    meal_relation: Mapped[str] = mapped_column(String(16), nullable=False, default="after")
    duration_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_label: Mapped[str | None] = mapped_column(String(60), nullable=True)
    quantity: Mapped[str | None] = mapped_column(String(40), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_prn: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Referral(AuditColumns, Base):
    """Referral out (and its follow-up)."""

    __tablename__ = "referral"
    __table_args__ = (Index("ix_referral_patient_id_referred_on", "patient_id", "referred_on"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    referring_dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    destination_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    destination_specialty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    destination_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    referred_on: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    followup_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    followup_on: Mapped[date | None] = mapped_column(Date, nullable=True)

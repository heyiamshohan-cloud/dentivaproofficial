"""Scheduling: appointments, status history and the daily queue (docs/04 §4).

One active queue entry per patient per day is enforced by a partial unique index
(``sqlite_where``), so the rule is guaranteed by the database, not by the UI.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from dentiva.data.base import AuditColumns, Base


class Appointment(AuditColumns, Base):
    """A booked slot. Status transitions are preserved in history rows."""

    __tablename__ = "appointment"
    __table_args__ = (
        Index(
            "ix_appointment_business_id_scheduled_start_utc", "business_id", "scheduled_start_utc"
        ),
        Index("ix_appointment_patient_id_scheduled_start_utc", "patient_id", "scheduled_start_utc"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    scheduled_start_utc: Mapped[datetime] = mapped_column(nullable=False)
    scheduled_end_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="scheduled")
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    queue_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("queue_entry.id", ondelete="SET NULL"), nullable=True
    )
    reminder_sent_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)


class AppointmentStatusHistory(Base):
    """Every status change, with the actor and the reason (REQ-APT-005)."""

    __tablename__ = "appointment_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    appointment_id: Mapped[int] = mapped_column(
        ForeignKey("appointment.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    to_status: Mapped[str] = mapped_column(String(24), nullable=False)
    changed_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    changed_at_utc: Mapped[datetime] = mapped_column(nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    rescheduled_from_utc: Mapped[datetime | None] = mapped_column(nullable=True)


class QueueEntry(AuditColumns, Base):
    """Today's waiting queue. Ticket numbers restart each local date."""

    __tablename__ = "queue_entry"
    __table_args__ = (
        Index(
            "ix_queue_entry_business_id_local_date_status", "business_id", "local_date", "status"
        ),
        Index(
            "uq_queue_entry_active_patient_per_day",
            "business_id",
            "local_date",
            "patient_id",
            unique=True,
            sqlite_where=text("status in ('waiting','called','in_consultation')"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    business_id: Mapped[int] = mapped_column(
        ForeignKey("business.id", ondelete="CASCADE"), nullable=False, index=True
    )
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patient.id", ondelete="CASCADE"), nullable=False, index=True
    )
    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointment.id", ondelete="SET NULL"), nullable=True
    )
    visit_id: Mapped[int | None] = mapped_column(
        ForeignKey("visit.id", ondelete="SET NULL"), nullable=True
    )
    dentist_id: Mapped[int | None] = mapped_column(
        ForeignKey("dentist.id", ondelete="SET NULL"), nullable=True
    )
    ticket_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="waiting")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    called_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    started_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at_utc: Mapped[datetime | None] = mapped_column(nullable=True)
    called_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    local_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

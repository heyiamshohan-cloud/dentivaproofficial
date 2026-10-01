"""ORM models, one module per aggregate (docs/04).

Importing this package registers every table on :data:`dentiva.data.base.Base.metadata`,
which is what Alembic autogenerate and the integrity checks walk. Keeping the
imports here means a new aggregate is visible to migrations as soon as it exists.
"""

from __future__ import annotations

from dentiva.data.base import Base
from dentiva.data.models.accounting import Expense, ExpenseCategory, Income
from dentiva.data.models.billing import (
    FinancialSummary,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentMethod,
)
from dentiva.data.models.clinical import (
    ClinicalCatalog,
    DentalChart,
    MedicineCatalog,
    Prescription,
    PrescriptionItem,
    Referral,
    ToothFinding,
    ToothStatusCatalog,
    TreatmentCatalog,
    TreatmentCategory,
    TreatmentRecord,
    Visit,
    VisitComplaint,
    VisitExamination,
)
from dentiva.data.models.identity import (
    Business,
    Dentist,
    DentistDesignation,
    DentistQualification,
    Designation,
    Qualification,
    Staff,
)
from dentiva.data.models.inventory import (
    InventoryBatch,
    InventoryCategory,
    InventoryItem,
    InventoryPurchase,
    InventoryPurchaseLine,
    StockMovement,
    Supplier,
)
from dentiva.data.models.ops import (
    ActivationRecord,
    Asset,
    AuditLog,
    BackupRecord,
    Notification,
    NotificationRead,
    NumberSequence,
    PrinterProfile,
    PrintJob,
    Setting,
)
from dentiva.data.models.patient import (
    Patient,
    PatientAttachment,
    PatientDuplicateFlag,
    PatientMergeLog,
)
from dentiva.data.models.scheduling import Appointment, AppointmentStatusHistory, QueueEntry
from dentiva.data.models.security import (
    PasswordHistory,
    Permission,
    Role,
    RolePermission,
    SessionRecord,
    User,
    UserRole,
)

__all__ = [
    "ActivationRecord",
    "Appointment",
    "AppointmentStatusHistory",
    "Asset",
    "AuditLog",
    "BackupRecord",
    "Base",
    "Business",
    "ClinicalCatalog",
    "DentalChart",
    "Dentist",
    "DentistDesignation",
    "DentistQualification",
    "Designation",
    "Expense",
    "ExpenseCategory",
    "FinancialSummary",
    "Income",
    "InventoryBatch",
    "InventoryCategory",
    "InventoryItem",
    "InventoryPurchase",
    "InventoryPurchaseLine",
    "Invoice",
    "InvoiceItem",
    "MedicineCatalog",
    "Notification",
    "NotificationRead",
    "NumberSequence",
    "PasswordHistory",
    "Patient",
    "PatientAttachment",
    "PatientDuplicateFlag",
    "PatientMergeLog",
    "Payment",
    "PaymentMethod",
    "Permission",
    "Prescription",
    "PrescriptionItem",
    "PrintJob",
    "PrinterProfile",
    "Qualification",
    "QueueEntry",
    "Referral",
    "Role",
    "RolePermission",
    "SessionRecord",
    "Setting",
    "Staff",
    "StockMovement",
    "Supplier",
    "ToothFinding",
    "ToothStatusCatalog",
    "TreatmentCatalog",
    "TreatmentCategory",
    "TreatmentRecord",
    "User",
    "UserRole",
    "Visit",
    "VisitComplaint",
    "VisitExamination",
]

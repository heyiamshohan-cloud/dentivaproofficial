"""First-run set-up (docs/05 §1, REQ-SET-001…004).

Start-up has three gates, in this order:

1. **Activated?** — the licence code has been accepted on this machine.
2. **Set up?** — a clinic exists with number sequences, roles and catalogs.
3. **Signed in?** — a session exists for a user.

:meth:`BootstrapService.state` answers the first two; :meth:`initialise` runs the
set-up wizard's work in a single transaction so a clinic is never half created.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.clock import utc_now
from dentiva.core.errors import ValidationError
from dentiva.data.models.accounting import ExpenseCategory
from dentiva.data.models.billing import PaymentMethod
from dentiva.data.models.clinical import (
    ClinicalCatalog,
    MedicineCatalog,
    ToothStatusCatalog,
    TreatmentCategory,
)
from dentiva.data.models.identity import Business, Dentist
from dentiva.data.models.ops import PrinterProfile
from dentiva.data.models.security import Role, User, UserRole
from dentiva.data.seed import (
    CLINICAL_CATALOGS,
    DEFAULT_PROFILE_FOR,
    EXPENSE_CATEGORIES,
    MEDICINES,
    PAYMENT_METHODS,
    PRINTER_PROFILES,
    TOOTH_STATUSES,
    TREATMENT_CATEGORIES,
)
from dentiva.data.seed.roles import ADMIN_ROLE
from dentiva.data.session import session_scope
from dentiva.domain.numbering import ensure_sequences
from dentiva.security import password as password_rules
from dentiva.services.rbac import internal, public_operation

#: Default currency (Bangladesh) and locale defaults for a new clinic.
DEFAULT_CURRENCY = "BDT"
DEFAULT_CURRENCY_SYMBOL = "৳"
DEFAULT_TIMEZONE = "Asia/Dhaka"


@dataclass(frozen=True, slots=True)
class SetupState:
    """What start-up still needs before the main window may open."""

    activated: bool
    has_business: bool
    has_administrator: bool
    business_name: str
    clinic_code: str

    @property
    def needs_activation(self) -> bool:
        return not self.activated

    @property
    def needs_setup(self) -> bool:
        return not (self.has_business and self.has_administrator)


class BootstrapService:
    """Create the clinic, the roles and the first administrator."""

    def __init__(self, session_factory: sessionmaker[DBSession]) -> None:
        self._session_factory = session_factory

    @public_operation
    def state(self, *, activated: bool) -> SetupState:
        """Public: describe how far set-up has progressed."""
        with session_scope(self._session_factory) as db:
            business = self._business(db)
            admins = int(
                db.execute(
                    select(func.count(User.id)).where(
                        User.is_system_admin.is_(True), User.is_active.is_(True)
                    )
                ).scalar_one()
            )
            return SetupState(
                activated=activated,
                has_business=business is not None,
                has_administrator=admins > 0,
                business_name=business.name if business else "",
                clinic_code=business.code if business else "",
            )

    @public_operation
    def initialise(
        self,
        *,
        clinic_name: str,
        admin_username: str,
        admin_password: str,
        admin_full_name: str = "",
        phone: str = "",
        address: str = "",
        city: str = "",
        dentist_name: str = "",
    ) -> SetupState:
        """Create the clinic, seed its catalogs and its first administrator.

        The whole set-up is one transaction: a failure leaves no partial clinic
        behind, and the wizard can simply be run again.
        """
        clean_name = (clinic_name or "").strip()
        if not clean_name:
            raise ValidationError("Enter the clinic name.")
        username = (admin_username or "").strip()
        if len(username) < 3:
            raise ValidationError("The administrator username must be at least three characters.")
        password_rules.validate_password(admin_password, username=username)
        with session_scope(self._session_factory) as db:
            if self._business(db) is not None:
                raise ValidationError("This database already holds a clinic; set-up is complete.")
            business = Business(
                name=clean_name,
                legal_name=clean_name,
                code=self._unique_code(db, clean_name),
                address_line1=(address or "").strip() or None,
                city=(city or "").strip() or None,
                phone_primary=(phone or "").strip() or None,
                country="Bangladesh",
                timezone=DEFAULT_TIMEZONE,
                currency_code=DEFAULT_CURRENCY,
                currency_symbol=DEFAULT_CURRENCY_SYMBOL,
                is_active=True,
                activated_at_utc=utc_now(),
            )
            db.add(business)
            db.flush()
            ensure_sequences(db, business.id)
            self._seed_catalogs(db, business.id)
            self._seed_printer_profiles(db, business.id)
            roles = self.role_service()
            roles.ensure_seeded(db)
            user = User(
                username=username,
                password_hash=password_rules.hash_password(admin_password),
                password_algo="argon2id",
                password_updated_at_utc=utc_now(),
                display_name=(admin_full_name or "").strip() or username,
                is_active=True,
                is_system_admin=True,
                must_change_password=False,
                session_timeout_minutes=15,
            )
            db.add(user)
            db.flush()
            admin_role = db.execute(select(Role).where(Role.name == ADMIN_ROLE)).scalar_one()
            db.add(UserRole(user_id=user.id, role_id=admin_role.id))
            if (dentist_name or "").strip():
                db.add(
                    Dentist(
                        business_id=business.id,
                        display_name=dentist_name.strip(),
                        is_active=True,
                    )
                )
            db.flush()
            return SetupState(
                activated=True,
                has_business=True,
                has_administrator=True,
                business_name=business.name,
                clinic_code=business.code,
            )

    @public_operation
    def ensure_catalogs(self, business_id: int) -> None:
        """Public: (re)seed the catalogs — safe to call on every start-up."""
        with session_scope(self._session_factory) as db:
            self.role_service().ensure_seeded(db)
            self._seed_catalogs(db, business_id)
            self._seed_printer_profiles(db, business_id)

    # ---------------------------------------------------------------- internals --
    @internal
    def role_service(self):
        from dentiva.services.role_service import RoleService

        return RoleService(self._session_factory)

    def _business(self, db: DBSession) -> Business | None:
        return db.execute(select(Business).order_by(Business.id)).scalars().first()

    def _unique_code(self, db: DBSession, name: str) -> str:
        base = (
            "".join(character.upper() for character in name if character.isalnum())[:12] or "CLINIC"
        )
        code, suffix = base, 1
        while db.execute(select(Business.id).where(Business.code == code)).scalar_one_or_none():
            suffix += 1
            code = f"{base}{suffix}"
        return code

    def _seed_catalogs(self, db: DBSession, business_id: int) -> None:
        existing_methods = set(db.execute(select(PaymentMethod.code)).scalars())
        for index, (code, label, requires_reference) in enumerate(PAYMENT_METHODS):
            if code not in existing_methods:
                db.add(
                    PaymentMethod(
                        code=code,
                        label=label,
                        requires_reference=requires_reference,
                        sort_order=index,
                    )
                )
        existing_statuses = set(db.execute(select(ToothStatusCatalog.code)).scalars())
        for index, (code, label, token, shape) in enumerate(TOOTH_STATUSES):
            if code not in existing_statuses:
                db.add(
                    ToothStatusCatalog(
                        code=code,
                        label=label,
                        color_token=token,
                        shape=shape,
                        sort_order=index,
                    )
                )
        existing_categories = set(db.execute(select(TreatmentCategory.name)).scalars())
        for index, name in enumerate(TREATMENT_CATEGORIES):
            if name not in existing_categories:
                db.add(TreatmentCategory(name=name, sort_order=index))
        existing_expenses = set(db.execute(select(ExpenseCategory.name)).scalars())
        for index, name in enumerate(EXPENSE_CATEGORIES):
            if name not in existing_expenses:
                db.add(ExpenseCategory(name=name, is_system=True, sort_order=index))
        existing_catalogs = {
            (row[0], row[1])
            for row in db.execute(select(ClinicalCatalog.kind, ClinicalCatalog.code)).all()
        }
        for kind, labels in CLINICAL_CATALOGS:
            for index, label in enumerate(labels):
                code = f"{kind}-{index + 1}"
                if (kind, code) not in existing_catalogs:
                    db.add(
                        ClinicalCatalog(
                            business_id=business_id,
                            kind=kind,
                            code=code,
                            label=label,
                            sort_order=index,
                        )
                    )
        existing_medicines = {
            (row[0], row[1], row[2])
            for row in db.execute(
                select(MedicineCatalog.name, MedicineCatalog.form, MedicineCatalog.strength)
            ).all()
        }
        for name, form, strength in MEDICINES:
            if (name, form, strength) not in existing_medicines:
                db.add(
                    MedicineCatalog(
                        business_id=None,
                        name=name,
                        form=form,
                        strength=strength,
                        is_active=True,
                    )
                )
        db.flush()

    def _seed_printer_profiles(self, db: DBSession, business_id: int) -> None:
        existing = set(db.execute(select(PrinterProfile.name)).scalars())
        for name, paper, width, height, base_font in PRINTER_PROFILES:
            if name in existing:
                continue
            db.add(
                PrinterProfile(
                    business_id=business_id,
                    name=name,
                    paper=paper,
                    width_mm=width,
                    height_mm=height,
                    base_font_pt=base_font,
                    is_default_for=next(
                        (key for key, value in DEFAULT_PROFILE_FOR.items() if value == name), None
                    ),
                    is_active=True,
                )
            )
        db.flush()

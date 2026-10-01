"""The service container: one object that owns every service.

The application shell, the UI screens and the tests all reach the service layer
through :class:`Services`. Every service shares the same ``session_factory``, so
a unit of work opened by :func:`~dentiva.services.rbac.require` and the services
calling each other stay inside one transaction.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Engine
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker

from dentiva.core.paths import AppPaths
from dentiva.data.session import session_factory
from dentiva.services.accounting_service import AccountingService
from dentiva.services.activation_service import ActivationService
from dentiva.services.appointment_service import AppointmentService
from dentiva.services.audit_service import AuditService
from dentiva.services.auth_service import AuthService
from dentiva.services.backup_service import BackupService
from dentiva.services.bootstrap_service import BootstrapService
from dentiva.services.inventory_service import InventoryService
from dentiva.services.invoice_service import InvoiceService
from dentiva.services.patient_service import PatientService
from dentiva.services.payment_service import PaymentService
from dentiva.services.reporting_service import ReportingService
from dentiva.services.role_service import RoleService
from dentiva.services.search_service import SearchService
from dentiva.services.settings_service import SettingsService
from dentiva.services.system_health_service import SystemHealthService
from dentiva.services.user_service import UserService
from dentiva.services.visit_service import VisitService

#: The services that expose protected methods, in the order they are built.
SERVICE_NAMES: tuple[str, ...] = (
    "patients",
    "visits",
    "appointments",
    "invoices",
    "payments",
    "accounting",
    "inventory",
    "search",
    "reporting",
    "users",
    "roles",
    "settings",
    "health",
    "backups",
)


@dataclass(frozen=True, slots=True)
class Services:
    """Every service, wired to one database."""

    session_factory: sessionmaker[DBSession]
    audit: AuditService
    activation: ActivationService
    auth: AuthService
    bootstrap: BootstrapService
    patients: PatientService
    visits: VisitService
    appointments: AppointmentService
    invoices: InvoiceService
    payments: PaymentService
    accounting: AccountingService
    inventory: InventoryService
    search: SearchService
    reporting: ReportingService
    users: UserService
    roles: RoleService
    settings: SettingsService
    health: SystemHealthService
    backups: BackupService

    @classmethod
    def create(
        cls,
        engine: Engine,
        *,
        paths: AppPaths | None = None,
        schema_version: str = "",
        app_version: str = "",
    ) -> Services:
        """Build every service bound to *engine*."""
        factory = session_factory(engine)
        resolved = paths or AppPaths.create().ensure()
        return cls(
            session_factory=factory,
            audit=AuditService(),
            activation=ActivationService(factory),
            auth=AuthService(factory),
            bootstrap=BootstrapService(factory),
            patients=PatientService(factory),
            visits=VisitService(factory),
            appointments=AppointmentService(factory),
            invoices=InvoiceService(factory),
            payments=PaymentService(factory),
            accounting=AccountingService(factory),
            inventory=InventoryService(factory),
            search=SearchService(factory),
            reporting=ReportingService(factory),
            users=UserService(factory),
            roles=RoleService(factory),
            settings=SettingsService(factory),
            health=SystemHealthService(
                factory,
                engine=engine,
                data_directory=str(resolved.data),
            ),
            backups=BackupService(
                factory,
                engine=engine,
                paths=resolved,
                schema_version=schema_version,
                app_version=app_version,
            ),
        )

    def protected_services(self) -> dict[str, object]:
        """The services whose methods carry permission declarations."""
        return {name: getattr(self, name) for name in SERVICE_NAMES}

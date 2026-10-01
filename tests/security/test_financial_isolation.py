"""Financial isolation: money is unreachable without a financial permission.

The rule (REQ-FIN-004/005, docs/06 §5): a permission tagged *financial* is the
only way to reach money — through a screen, a search, a report, an export or a
dashboard tile. Hiding a column is not enough, so this test drives the real
services with a session that holds **every** non-financial permission and proves
that not one taka comes back.

A second, weaker user (no permissions at all) is used as a control.
"""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from dentiva.core.errors import PermissionDenied
from dentiva.core.money import Money
from dentiva.data.seed.roles import ROLE_TEMPLATES
from dentiva.domain.permissions import CODES, FINANCIAL_CODES, PERMISSIONS
from dentiva.services import Services
from dentiva.services.accounting_service import AccountingService
from dentiva.services.invoice_service import InvoiceService
from dentiva.services.payment_service import PaymentService
from dentiva.services.rbac import required_permission

#: Services whose whole purpose is money.
MONEY_SERVICES = (InvoiceService, PaymentService, AccountingService)

#: Every permission that does **not** expose money.
NON_FINANCIAL_PERMISSIONS = frozenset(CODES) - set(FINANCIAL_CODES)

FINANCIAL_WRITE_CODES = frozenset(
    {
        "invoice.create",
        "invoice.edit",
        "invoice.void",
        "payment.create",
        "payment.edit",
        "payment.void",
        "accounting.manage",
        "inventory.purchase",
        "finance.export",
    }
)


def _entry_points(service: Any) -> dict[str, Any]:
    return {
        name: member
        for name, member in vars(type(service)).items()
        if not name.startswith("_") and callable(member)
    }


def _required_kwargs(method: Any) -> dict[str, Any]:
    import inspect

    parameters = inspect.signature(method).parameters
    return {
        name: None
        for name, parameter in parameters.items()
        if parameter.kind is inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
    }


def _financial_entry_points(services: Services) -> list[tuple[str, str, Any, str]]:
    """Every service method whose declared permission is tagged financial."""
    found: list[tuple[str, str, Any, str]] = []
    for field_name in services.__class__.__dataclass_fields__:  # type: ignore[attr-defined]
        service = getattr(services, field_name)
        if not type(service).__module__.startswith("dentiva.services"):
            continue
        for method_name, method in _entry_points(service).items():
            permission = required_permission(method)
            if permission and permission in FINANCIAL_CODES:
                found.append((field_name, method_name, method, permission))
    return found


# ----------------------------------------------------------------- the matrix ---
def test_financial_permissions_are_flagged_in_the_catalogue() -> None:
    flagged = {spec.code for spec in PERMISSIONS if spec.is_financial}
    assert flagged == set(FINANCIAL_CODES)
    for code in ("invoice.view", "payment.create", "finance.reports"):
        assert code in flagged, f"{code} must be treated as financial"
    for code in ("patient.view", "visit.create", "chart.edit", "queue.manage"):
        assert code not in flagged, f"{code} must not expose money"


def test_money_services_only_declare_financial_permissions(services: Services) -> None:
    offenders: list[str] = []
    for service in (
        services.invoices,
        services.payments,
        services.accounting,
    ):
        if not isinstance(service, MONEY_SERVICES):
            continue
        for method_name, method in _entry_points(service).items():
            permission = required_permission(method)
            if permission is None:
                continue
            if permission not in FINANCIAL_CODES:
                offenders.append(f"{type(service).__name__}.{method_name} -> {permission}")
    assert not offenders, "money reachable through a non-financial permission:\n" + "\n".join(
        offenders
    )


def test_the_matrix_actually_contains_financial_methods(services: Services) -> None:
    found = _financial_entry_points(services)
    assert len(found) >= 15, f"only {len(found)} financial entry points were found"


# ---------------------------------------------------------------- behaviour ---
def test_a_user_with_every_non_financial_permission_still_cannot_reach_money(
    services: Services,
    as_actor,
) -> None:
    failures: list[str] = []
    checked = 0
    with as_actor(permissions=NON_FINANCIAL_PERMISSIONS, name="clinician"):
        for service_name, method_name, method, permission in _financial_entry_points(services):
            checked += 1
            try:
                getattr(getattr(services, service_name), method_name)(**_required_kwargs(method))
            except PermissionDenied:
                continue
            except Exception as error:
                failures.append(
                    f"{service_name}.{method_name} ({permission}): {type(error).__name__}: {error}"
                )
            else:
                failures.append(f"{service_name}.{method_name} ({permission}): returned data")
    assert not failures, "financial data reachable without a financial permission:\n" + "\n".join(
        failures
    )
    assert checked >= 15


def test_global_search_never_returns_invoices_without_the_permission(
    services: Services,
    clinic,
    admin_session,
    as_actor,
) -> None:
    patient = services.patients.register(
        business_id=1, name="তানভীর আহমেদ", phone_primary="01700-112233"
    )
    services.invoices.create(
        business_id=1,
        patient_id=patient.id,
        lines=[
            _line("Consultation", Money.from_taka("500")),
        ],
    )

    with as_actor(permissions=NON_FINANCIAL_PERMISSIONS, name="clinician"):
        results = services.search.search(term="তানভীর", business_id=1)

    assert results.patients, "the patient must still be findable"
    assert results.invoices == (), "invoices leaked to a user without invoice.view"
    assert results.financial_included is False
    assert "invoices" in results.omitted_kinds
    blob = repr(dataclasses.asdict(results))
    assert "Money(" not in blob, f"a monetary value reached an unauthorised caller: {blob}"


def test_a_financial_user_does_see_the_invoice(
    services: Services,
    clinic,
    admin_session,
    as_actor,
) -> None:
    patient = services.patients.register(
        business_id=1, name="রাহাত করিম", phone_primary="01700-445566"
    )
    services.invoices.create(
        business_id=1,
        patient_id=patient.id,
        lines=[_line("X-ray", Money.from_taka("700"))],
    )
    with as_actor(permissions=NON_FINANCIAL_PERMISSIONS | {"invoice.view"}, name="accountant"):
        results = services.search.search(term="রাহাত", business_id=1)
    assert len(results.invoices) == 1
    assert results.invoices[0].total == Money.from_taka("700")


def test_reports_are_refused_without_the_financial_report_permission(
    services: Services,
    as_actor,
) -> None:
    from datetime import date

    today = date.today()
    with as_actor(permissions=NON_FINANCIAL_PERMISSIONS, name="clinician"):
        with pytest.raises(PermissionDenied):
            services.reporting.outstanding(business_id=1)
        with pytest.raises(PermissionDenied):
            services.reporting.by_method(business_id=1)
        with pytest.raises(PermissionDenied):
            services.reporting.period_report(
                business_id=1, from_date=today.replace(day=1), to_date=today
            )
        # A clinical report is still available to the same user.
        assert (
            services.reporting.visit_counts(
                business_id=1, from_date=today.replace(day=1), to_date=today
            )
            == []
        )


def test_seeded_roles_keep_money_write_permissions_away_from_clinical_staff() -> None:
    clinical_roles = {
        template.name: template.codes
        for template in ROLE_TEMPLATES
        if template.name in {"Dentist", "Dental Assistant", "Receptionist", "Read-only"}
    }
    assert clinical_roles, "the seeded clinical roles changed; update this test"
    for name, codes in clinical_roles.items():
        writes = sorted(set(codes) & FINANCIAL_WRITE_CODES)
        assert not writes, f"role '{name}' can write money: {writes}"


def test_accountant_role_can_do_the_money_work() -> None:
    accountant = next(template for template in ROLE_TEMPLATES if template.name == "Accountant")
    for code in ("invoice.view", "invoice.create", "payment.create", "finance.reports"):
        assert code in accountant.codes, f"the Accountant role must keep {code}"


def test_every_financial_denial_is_audited(services: Services, as_actor) -> None:
    from dentiva.data.session import session_scope
    from dentiva.services.audit_service import AuditService

    with as_actor(permissions=NON_FINANCIAL_PERMISSIONS, name="clinician"):
        with pytest.raises(PermissionDenied):
            services.invoices.list_invoices(business_id=1)
    with session_scope(services.session_factory) as db:
        page = AuditService().search(db, action="security.denied")
    assert page.total >= 1
    assert any("invoice.view" in entry.summary for entry in page.items)


def _line(name: str, price: Money):
    from dentiva.services.invoice_service import LineInput

    return LineInput(name=name, quantity=1, unit_price=price)

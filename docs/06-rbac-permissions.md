# Dentiva Pro — RBAC permission catalogue (Phase 1)

Single source of truth at runtime: `dentiva/domain/permissions.py` (seeded into the
`permission` table). Every service method declares exactly one permission via
`@require(...)`. Financial permissions are tagged `is_financial=True` so the
security test matrix can assert that no financial data leaks through any path.
Permissions marked **S** are *sensitive*: they additionally require password
re-authentication even for a user who holds them.

## 1. Catalogue

### Patients
| Code | Meaning | Flags |
|---|---|---|
| `patient.view` | Open patient list/profile, see demographics | |
| `patient.create` | Register a patient | |
| `patient.edit` | Edit patient demographics/history | |
| `patient.archive` | Archive (soft-delete) a patient | |
| `patient.delete` | Hard-delete a patient and (separately gated) its history | **S** |
| `patient.merge` | Merge duplicate patients | **S** |
| `patient.export` | Export patient data (CSV/XLSX) | |
| `patient.import` | Import patients from CSV | |
| `attachment.view` | View/download attachments | |
| `attachment.upload` | Upload attachments | |
| `attachment.delete` | Delete attachments | **S** |

### Clinical
| Code | Meaning | Flags |
|---|---|---|
| `visit.view` | View visits | |
| `visit.create` | Start a visit | |
| `visit.edit` | Edit a visit (audited) | |
| `visit.delete` | Cancel/delete a visit | **S** |
| `chart.view` | View the dental chart | |
| `chart.edit` | Record/change tooth findings | |
| `prescription.view` | View prescriptions | |
| `prescription.create` | Create a prescription | |
| `prescription.edit` | Edit a prescription | |
| `prescription.delete` | Delete a prescription | **S** |
| `prescription.print` | Print/export a prescription PDF | |
| `treatment.view` | View treatments/treatment catalog | |
| `treatment.record` | Record treatments on a visit | |
| `treatment.manage` | Maintain the treatment catalog | |
| `clinical_catalog.manage` | Maintain complaint/examination/advice catalogs | |
| `referral.view` | View referrals | |
| `referral.create` / `referral.edit` | Create/edit referrals | |

### Scheduling
| Code | Meaning | Flags |
|---|---|---|
| `appointment.view` | View appointments | |
| `appointment.create` | Create appointments | |
| `appointment.edit` | Edit/reschedule | |
| `appointment.delete` | Cancel/delete | |
| `appointment.complete` | Mark completed/no-show | |
| `queue.view` | View the queue | |
| `queue.manage` | Call/skip/complete/reorder the queue | |

### Billing & finance
| Code | Meaning | Flags |
|---|---|---|
| `invoice.view` | View invoices | financial |
| `invoice.create` | Create an invoice | financial |
| `invoice.edit` | Edit a draft/issued invoice | financial |
| `invoice.void` | Void an invoice | financial, **S** |
| `invoice.print` | Print/export invoices | financial |
| `payment.view` | View payments | financial |
| `payment.create` | Record a payment | financial |
| `payment.edit` | Edit a payment | financial, **S** |
| `payment.void` | Void/refund a payment | financial, **S** |
| `finance.reports` | Financial reports & accounting summaries | financial |
| `accounting.view` | View income/expense records | financial |
| `accounting.manage` | Create/edit/delete income & expenses | financial |
| `finance.export` | Export financial data | financial |

### Inventory
| Code | Meaning | Flags |
|---|---|---|
| `inventory.view` | View inventory, stock, alerts | |
| `inventory.manage` | Create/edit/deactivate items, suppliers | |
| `inventory.purchase` | Record purchases (affects stock & accounting) | financial |
| `inventory.adjust` | Stock adjustments/usage | |

### People & administration
| Code | Meaning | Flags |
|---|---|---|
| `staff.view` / `staff.manage` | View/maintain staff records | |
| `user.view` / `user.manage` | View/maintain users (create, activate, reset password) | **S** (password reset) |
| `role.view` / `role.manage` | View/maintain roles & permissions | **S** |
| `settings.view` / `settings.manage` | View/change clinic & system settings | **S** (security-related) |
| `printer.manage` | Maintain printer & paper profiles | |
| `audit.view` | View the audit log | **S** |
| `system.health` | Run/see system health & integrity reports | |
| `notification.view` | See notifications (filtered by their own permissions) | |

### Data lifecycle
| Code | Meaning | Flags |
|---|---|---|
| `backup.create` | Create/verify a backup | |
| `backup.restore` | Restore from a backup | **S** |
| `data.export` | Export any permitted dataset | |
| `data.import` | Import data | |
| `data.delete` | Hard-delete records | **S** |
| `business.delete` | Delete a business and all of its data | **S** |
| `app.reset` | Reset the application to factory state | **S** |

## 2. Seeded role templates (fully editable; not hard-coded behaviour)

| Role | Permissions (summary) |
|---|---|
| **Administrator** | everything, including `business.delete`, `app.reset`, `backup.restore`, `audit.view`, `role.manage` |
| **Dentist** | patients view/create/edit, all clinical (visits, chart, prescriptions, treatments, referrals), appointments view/create, queue view, `treatment.view`; **no** invoicing, payments, accounting or user administration unless granted |
| **Receptionist** | patients create/edit, appointments full, queue manage, `visit.view`, `invoice.view`, `payment.view` (optional); no clinical writing, no editing of financial records |
| **Dental Assistant** | `patient.view`, `visit.view/create`, `chart.view`, `queue.manage`, `inventory.view`, `inventory.adjust`; no prescriptions, no billing writes |
| **Accountant** | `invoice.view/create/edit/print`, full payments, `finance.reports`, `accounting.*`, `finance.export`, `patient.view`, `data.export`; no clinical writes |
| **Inventory Manager** | `inventory.*`, `supplier` management, `patient.view` (for usage attribution); nothing else |
| **Read-only / Auditor** | `*.view` across permitted areas, `audit.view`, `system.health`; no mutation |

Roles are stored data: an administrator can create **Custom** roles and tick any
permission, and can clone a template. The only implicit rule is that the built-in
Administrator role cannot be stripped of `role.manage` while no other role holds it
(guard against lockout).

## 3. Enforcement points (defence in depth)
1. **Service decorator** (`@require`) — mandatory and authoritative.
2. **Audit** — every denied attempt is recorded (`severity=security`).
3. **UI state** — widgets are disabled or rendered as a *no-permission* state when
   the permission is absent (usability, never the security boundary).
4. **Search / export / reports / dashboard** — each goes through the same services;
   results are filtered server-side (service layer), not post-filtered in the UI.
5. **Tests** — `tests/security/test_permission_matrix.py` iterates every service
   method, introspects its required permission and asserts denial for a user
   lacking it; `test_financial_isolation.py` asserts a non-financial user receives
   nothing from financial services, search, export, reports or dashboard widgets.

## 4. Permission-changing rules
- Changing a role's permissions requires `role.manage` + re-authentication and is
  audited with before/after.
- A user's own effective permissions are re-evaluated immediately (signal bus);
  open screens refresh into their permitted state.
- Deactivating a user does not delete history: `user.is_active=false`, all audit
  references intact.

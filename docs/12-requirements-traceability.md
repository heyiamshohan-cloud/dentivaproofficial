# Dentiva Pro — Requirements traceability matrix

Status values: **P** planned (Phase 1) · **IP** in progress · **I** implemented ·
**V** verified (test passing) · **R** released.
At every phase gate this file is updated; `tools/trace_report.py` cross-checks it
against the test suite and fails the release when a mandatory (M) requirement is
not at least **V**.

Columns: **Impl** = implementation target (module/service/entity) ·
**Screen** = UI location · **Test** = test target (file or procedure).

**Last updated: end of Phase 2** (repository, engineering foundation, design
system). Rows that Phase 2 delivered are marked **I** (implemented) or **V**
(verified by a passing test); **IP** marks a requirement delivered in part
(the remainder belongs to a later phase, named in the row). Everything else is
still **P**.

---

## GEN — General
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| GEN-001 | Product name Dentiva Pro | `src/dentiva/ui/shell/main_window.py`, `core/paths.py`, docs | all | `tests/ui/test_shell.py` | V |
| GEN-002 | English UI | every user-visible string in `src/dentiva/ui/**` | all | `tests/ui/test_components.py`, `tests/ui/test_shell.py` + screenshot review | I |
| GEN-003 | Unicode/Bangla user content | `core/textutil.py`, `assets/fonts`, `ui/theme/fonts.py` | all | `tests/unit/test_textutil.py`, `tests/unit/test_icons_bengali.py`, `tests/integration/test_database.py` | V |
| GEN-004 | BDT / ৳ currency | `core/money.py` (integer paisa), `data/base.py::MoneyType` | all | `tests/unit/test_money.py` | V |
| GEN-005 | Offline, no cloud/SaaS/paid SDK | no networking import anywhere in `src/` | — | `tests/unit/test_no_network_imports.py` | V |
| GEN-006 | No data leaves the machine | `test_no_network_imports.py` + dependency audit | — | `tests/unit/test_no_network_imports.py` | V |
| GEN-007 | Dependency audit | `docs/15`, `THIRD_PARTY_NOTICES.md`, `licenses/` | About | CI `hygiene` job + `tests/ui/test_about_view.py` | I |
| GEN-008 | No artificial record caps | services/repositories (paging only) | all lists | `tests/stress/test_volume.py` | P |
| GEN-009 | No fake buttons/mocks/demo data | code review + dead-code job | — | `tests/ui/test_no_dead_buttons.py` | P |
| GEN-010 | No TODO/FIXME for unfinished work | CI grep | — | CI `hygiene` job | V |
| GEN-011 | No broken navigation | `ui/shell/navigation.py` | sidebar | `tests/ui/test_navigation_matrix.py` | P |
| GEN-012 | No disabled mandatory workflow | review | — | phase gate checklist | P |
| GEN-013 | No dead code | `vulture src tests --min-confidence 80` | — | CI `dead-code` job | V |
| GEN-014 | v1.0.0 final production | release process | About | release gate | P |
| GEN-015 | No "future" excuse gaps | phase DoD | — | phase gate | P |
| GEN-016 | Win10 1809+/Win11 x64 | installer, `core/paths` | — | CI install matrix | P |
| GEN-017 | Documented non-goals | `docs/03` §18 | — | n/a | P |

## BIZ — Business relationship & scale
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| BIZ-001 | Connected patient lifecycle | FKs across all aggregates | profile/timeline | `tests/integration/test_lifecycle.py` | P |
| BIZ-002 | Correct patient/visit/dentist/invoice/payment linkage | service layer invariants | — | `test_lifecycle.py` | P |
| BIZ-003 | Multi-dentist + actor identity | `dentist`, `*_by_user_id`, `*_dentist_id` | Clinical | `tests/unit/test_actor_identity.py` | P |
| BIZ-004 | Unlimited patients & history | paging everywhere | lists/timeline | `tests/stress/test_volume.py` | P |

## FRS — First-run setup
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| FRS-001 | Setup wizard on first launch | `services/setup_service.py`, `ui/shell/SetupWizard` | wizard | `tests/ui/test_setup_wizard.py` | P |
| FRS-002 | Clinic identity + logo | `business`, `asset` | wizard step 1 / Settings | `tests/unit/test_clinic_service.py` | P |
| FRS-003 | One or many dentists with professional details | `dentist`, `dentist_designation`, `dentist_qualification` | wizard step 2 | `tests/unit/test_dentist_service.py` | P |
| FRS-004 | Multiple designations & qualifications | normalised tables | wizard/Settings | `test_dentist_service.py` | P |
| FRS-005 | Initial admin account, Argon2id | `user`, `security/password` | wizard step 3 | `tests/unit/test_password.py` | P |
| FRS-006 | Currency/print/backup/security defaults | `settings`, `printer_profile` | wizard step 4 | `tests/unit/test_settings_service.py` | P |
| FRS-007 | Transactional + recoverable setup | single transaction, rollback | wizard | `tests/integration/test_setup_rollback.py` | P |
| FRS-008 | Production blocked until setup complete | boot gate in `app.py` | — | `tests/integration/test_setup_gate.py` | P |
| FRS-009 | Stepper UX with validation | `ui/shell/SetupWizard`, `Stepper` | wizard | `test_setup_wizard.py` | P |
| FRS-010 | Logo validation & storage | `attachment/asset` validators | wizard/Settings | `tests/unit/test_asset_validation.py` | P |

## SHL — Shell
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| SHL-001 | Professional window shell | `src/dentiva/ui/shell/main_window.py` | shell | `tests/ui/test_shell.py` | V |
| SHL-002 | Header: brand, clinic name, date *(notifications & user menu: Phase 4)* | `src/dentiva/ui/shell/header.py` | header | `tests/ui/test_shell.py` | IP |
| SHL-003 | Collapsible sidebar, both states functional | `src/dentiva/ui/shell/sidebar.py` | sidebar | `tests/ui/test_shell.py` | V |
| SHL-004 | Navigation groups exactly as specified | `src/dentiva/ui/shell/navigation.py` | sidebar | `tests/ui/test_shell.py` | V |
| SHL-005 | Audit Log, System Health, Search, Notifications, Print Center | registry entries exist; screens land with their phases (3/4/13/14) | Admin/header | `tests/ui/test_shell.py` | IP |
| SHL-006 | Sidebar state persistence | `src/dentiva/ui/settings.py` (`<data>/ui.ini`) | sidebar | `tests/ui/test_shell.py` | V |
| SHL-007/008 | Every item real; none decorative | registry + `ui/views/pending.py` build-state indicator | — | `tests/ui/test_shell.py::test_no_module_stays_pending_past_its_phase` | IP |
| SHL-009 | Screen title + contextual actions | header/screen chrome (Phase 4) | all | layout audit | P |

## UIX — Premium UI/UX
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| UIX-001 | Premium clinical design language | `src/dentiva/ui/theme/tokens.py`, `theme/qss.py` | all | `tests/unit/test_theme.py` + screenshot review | I |
| UIX-002 | Not generic; integrated controls | `src/dentiva/ui/components/*` | all | `tests/ui/test_components.py` + layout audit | I |
| UIX-003 | Full design system + all states | `src/dentiva/ui/components/*` | all | `tests/ui/test_components.py` | V |
| UIX-004 | Alignment, no overflow, centred icons | tokens + `ui/diagnostics.py` audit | all | `tests/ui/test_layout_audit.py` | V |
| UIX-005 | No clipping/overlap/broken scrolling | `ui/diagnostics.py` | all | `tests/ui/test_layout_audit.py` | V |
| UIX-006 | No visually-present-but-inactive controls | component contract | all | `test_no_dead_buttons.py` | P |
| UIX-007 | Subtle purposeful animation | `ui/theme/animations.py` | shell/dialogs | manual + timer tests | P |
| UIX-008 | Loading/empty/error/success/disabled/no-permission/validation | `ui/components/states.py`, `feedback.py` | all | `tests/ui/test_components.py` | V |
| UIX-009 | Single token source, generated QSS | `src/dentiva/ui/theme/tokens.py` → `theme/qss.py` | — | `tests/unit/test_theme.py` | V |

## RSP — Responsive & High-DPI
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| RSP-001 | 1366×768 … 3840×2160 | `ui/diagnostics.py` | all | `tests/ui/test_layout_audit.py` | V |
| RSP-002 | 100/125/150/175/200 % scaling | `theme/__init__.py::configure_high_dpi`, SVG icons | all | `tests/ui/test_layout_audit.py` (1.0–2.0 sweep) + Windows CI | V |
| RSP-003 | Usable at 1366×768 | min-size audit (1024×640 floor) | all | `tests/ui/test_layout_audit.py` | V |
| RSP-004 | Layout rules, not scroll-everywhere | audit rule `horizontal-scroll` | all | `tests/ui/test_layout_audit.py` | V |
| RSP-005 | Deliberate responsive grid (6 cards → 3+3) | `src/dentiva/ui/components/layout.py::ResponsiveGrid` | Dashboard etc. | `tests/ui/test_responsive_grid.py` | V |
| RSP-006 | Every screen reviewed at many sizes | `--audit-layout` (16 screens × 5 resolutions) | all | `tests/ui/test_layout_audit.py`, `tests/ui/test_cli.py` | V |

## ICO — Icon & branding
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| ICO-001/002 | Premium concept, transparent, optical centring | `assets/icons/dentiva.png` (master, pending) | all | manual review | P |
| ICO-003 | No background rectangle/stretch | master + verification script | — | `tools/build/verify_icon.py` | P |
| ICO-004 | True multi-resolution .ico | `tools/build/make_ico.py` (Pillow) | — | `tests/unit/test_icon_asset.py` | P |
| ICO-005 | Icon in exe, installer, shortcuts, taskbar, title bar | Inno Setup + `AppUserModelID` | — | CI install assertions | P |
| ICO-006 | Master PNG reused in About/print | `assets/` | About/documents | `test_icon_asset.py` | P |

## PAT — Patients
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| PAT-001 | Unlimited patients | repository paging | Patients | `tests/stress/test_volume.py` | P |
| PAT-002 | Period filters (today/7/30/90/1y/all/custom) | `domain/period.py` | Patients | `tests/ui/test_patient_filters.py` | P |
| PAT-003 | New/recent first ordering | query ordering | Patients | `tests/unit/test_patient_queries.py` | P |
| PAT-004 | Full registration fields | `patient` + form sections | Patient form | `tests/unit/test_patient_service.py` | P |
| PAT-005 | Sectioned/tabbed form | `ui/views/patients/patient_form.py` | Patient form | layout audit | P |
| PAT-006 | Unique validated patient code | `numbering`, unique index | Patient form | `tests/unit/test_numbering.py` | P |
| PAT-007 | Duplicate detection (phone/name/DOB) | `domain/duplicates.py` | Duplicate dialog | `tests/unit/test_duplicates.py` | P |
| PAT-008 | Never silently merge | explicit merge service + audit | Merge dialog | `tests/integration/test_merge.py` | P |
| PAT-009 | Paged searchable list | repository + table | Patients | `tests/ui/test_patients_view.py` | P |
| PAT-010 | Permission-controlled CRUD | `patient.*` perms | Patients | `tests/security/test_permission_matrix.py` | P |

## PRF — Patient profile
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| PRF-001 | Click patient → profile | `ui/views/patients/profile.py` | Patients → profile | `tests/ui/test_patient_profile.py` | P |
| PRF-002 | 13 sections incl. timeline/chart/financial history | tab registry | profile | `test_patient_profile.py` | P |
| PRF-003 | Activity, visit count, treatments, prescriptions, invoices/payments | `dashboard_service`/repos | Overview | `tests/integration/test_profile_data.py` | P |
| PRF-004 | Billed/paid/outstanding + settlement links | `repositories.finance` | Financial History | `tests/unit/test_financial_history.py` | P |
| PRF-005 | Referrals + future appointments | `referral`, `appointment` | Referrals/Appointments | `test_profile_data.py` | P |
| PRF-006 | Context actions (visit/appointment/prescription/invoice/payment) | profile header | profile | `tests/ui/test_profile_actions.py` | P |
| PRF-007 | Inherited patient context | action intents | dialogs | `test_profile_actions.py` | P |
| PRF-008 | Profile header with alerts | profile header | profile | layout audit | P |

## VIS — Visits
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| VIS-001 | Repeat visits preserved separately | `visit` | Visits tab | `tests/integration/test_visits.py` | P |
| VIS-002 | Full visit capture | `visit` + children | Visit editor | `tests/unit/test_visit_service.py` | P |
| VIS-003 | No overwrite of history | insert-only rules | — | `test_visits.py` | P |
| VIS-004 | Controlled + audited edit | `visit.edit` + audit before/after | Visit editor | `tests/security/test_audit_entries.py` | P |
| VIS-005 | Visit status lifecycle | `visit.status` | Visits | `tests/unit/test_visit_state.py` | P |

## TML — Clinical timeline
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| TML-001 | Timeline of all event types | `domain/timeline.py` projection | Timeline tab | `tests/unit/test_timeline.py` | P |
| TML-002 | Date/time, type, actor, summary | timeline DTO | Timeline | `test_timeline.py` | P |
| TML-003 | Scannable + navigable | filters + click-through | Timeline | `tests/ui/test_timeline_view.py` | P |
| TML-004 | Performant for huge histories | incremental loading | Timeline | `tests/stress/test_long_timeline.py` | P |

## CHT — Dental chart
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| CHT-001 | Interactive painted chart widget | `ui/components/dental_chart.py` | Dental Chart tab | `tests/ui/test_dental_chart.py` | P |
| CHT-002 | Adult + paediatric, documented notation (FDI) | `domain/dental.py` | Dental Chart | `tests/unit/test_tooth_numbering.py` | P |
| CHT-003 | Single & multi tooth selection | chart widget | Dental Chart | `test_dental_chart.py` | P |
| CHT-004 | Findings per tooth/surface/visit | `tooth_finding` | Dental Chart | `tests/unit/test_chart_service.py` | P |
| CHT-005 | Historical state / as-of visit | projection over findings | Dental Chart | `test_chart_service.py` | P |
| CHT-006 | Status catalogue + legend | `tooth_status_catalog` | Dental Chart | `test_chart_service.py` | P |
| CHT-007 | Never clipped/overlapping | layout + audit | Dental Chart | `layout_audit.py` | P |

## TRT — Treatment catalog
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| TRT-001 | Configurable catalog | `treatment_catalog` | Treatments | `tests/unit/test_treatment_service.py` | P |
| TRT-002 | No hard-coded prices | catalog-driven | everywhere | grep test `test_no_hardcoded_prices.py` | P |
| TRT-003 | Admin can modify | `treatment.manage` | Treatments | `test_treatment_service.py` | P |
| TRT-004 | Price/name snapshot on invoice | `invoice_item` snapshots | Invoice | `tests/unit/test_invoice_math.py` | P |

## PRX — Prescriptions
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| PRX-001 | Create from profile and from Prescriptions | `prescription_service` | Prescriptions/profile | `tests/ui/test_prescription_editor.py` | P |
| PRX-002 | Multiple medicines | `prescription_item` | editor | `tests/unit/test_prescription_service.py` | P |
| PRX-003 | Full medicine field set | `prescription_item` columns | editor | `test_prescription_service.py` | P |
| PRX-004 | Structured + free text | editor design | editor | `test_prescription_editor.py` | P |
| PRX-005 | Prescriber identity + designations + qualifications | document header block | document/PDF | `tests/print/test_prescription_pdf.py` | P |
| PRX-006 | Medicine catalog/autocomplete | `medicine_catalog` | editor | `test_prescription_service.py` | P |
| PRX-007 | Permission control | `prescription.*` | — | `test_permission_matrix.py` | P |

## CLN — Clinical catalogs
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| CLN-001 | Selectable complaints/findings | `clinical_catalog` + pickers | Visit editor | `tests/ui/test_clinical_pickers.py` | P |
| CLN-002 | No repetitive typing | multi-select chips | Visit editor | `test_clinical_pickers.py` | P |
| CLN-003 | Custom/free text allowed | `free_text` columns | Visit editor | `test_visit_service.py` | P |
| CLN-004 | Configurable vocabulary | Settings → Clinical catalogs | Settings | `tests/unit/test_catalog_service.py` | P |

## DOC — Prescription document
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| DOC-001 | Ultra-premium document | `documents/templates/prescription.py` | preview/print | `tests/print/test_prescription_pdf.py` | P |
| DOC-002 | Clinic + dentist header block | document model | print | `test_prescription_pdf.py` | P |
| DOC-003 | Patient block | document model | print | `test_prescription_pdf.py` | P |
| DOC-004 | C/C, O/E, R/E/Advice | clinical block (configurable labels) | print | `test_prescription_pdf.py` | P |
| DOC-005 | Clear multi-medicine table | medicine table block | print | `tests/print/test_long_prescription.py` | P |
| DOC-006 | Configurable footer | `printer_profile.footer_text` | print/Settings | `test_prescription_pdf.py` | P |
| DOC-007 | Blank signature area | `SignatureBlock` (no text inside) | print | `tests/print/test_signature_area.py` | P |
| DOC-008 | Print + PDF | preview + QPdfWriter | Print dialog | `test_prescription_pdf.py` | P |
| DOC-009 | Long content safe | pagination tests | preview | `test_long_prescription.py` | P |

## PRT — Printing engine
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| PRT-001 | Model → Layout → Profile → Preview → Printer → Output | `documents/*` | Print Center | `tests/print/test_engine.py` | P |
| PRT-002 | A4/A5/58/80/mini/custom | `documents/profiles.py` | profile selector | `tests/print/test_paper_profiles.py` | P |
| PRT-003 | All Windows printers | `QPrinterInfo` + native dialog | Print dialog | Windows CI print job | P |
| PRT-004 | No paid SDK | Qt only | — | dependency audit | P |
| PRT-005 | No overlap/clipping when paper changes | engine re-layout | preview | `test_paper_profiles.py` | P |
| PRT-006 | Preview for every printable | `PrintPreviewDialog` | preview | `tests/ui/test_print_preview.py` | P |
| PRT-007 | Printer selection | `QPrintDialog` + profiles | Print dialog | Windows CI | P |
| PRT-008 | PDF output | `QPdfWriter` | Save as PDF | `test_engine.py` | P |
| PRT-009 | Unicode/Bengali in PDF | embedded subsets | — | `tests/print/test_unicode_pdf.py` | P |
| PRT-010 | High-DPI sharpness | vector text, DPR-aware preview | preview | `tests/print/test_preview_dpi.py` | P |
| PRT-011 | Print Center | `ui/dialogs/print_center.py` | Print Center | `tests/ui/test_print_center.py` | P |

## INV — Invoices
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| INV-001 | Branded invoice header | `documents/templates/invoice.py` | preview | `tests/print/test_invoice_pdf.py` | P |
| INV-002 | No dentist signature by default | template config | preview | `test_invoice_pdf.py` | P |
| INV-003 | Line item fields | `invoice_item` | Invoice editor | `tests/unit/test_invoice_math.py` | P |
| INV-004 | Subtotal/discount/total/paid/due/status | `domain/invoice_math.py` | Invoice | `test_invoice_math.py` | P |
| INV-005 | Full/partial/no/later payment | `invoice_service`, `payment_service` | Invoice/Payments | `tests/integration/test_invoice_lifecycle.py` | P |
| INV-006 | Payments linked to invoice | `payment.invoice_id` | Invoice | `test_invoice_lifecycle.py` | P |
| INV-007 | All paper sizes, long lists | invoice template + pagination | preview | `tests/print/test_long_invoice.py` | P |
| INV-008 | Unique sequential numbering | `number_sequence` + unique index | Invoice | `tests/unit/test_numbering.py` | P |
| INV-009 | Audited void, record preserved | `invoice.void` | Invoice | `tests/unit/test_invoice_void.py` | P |

## PAY — Payments
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| PAY-001 | Payment ledger fields | `payment` | Payments | `tests/unit/test_payment_service.py` | P |
| PAY-002 | Cash/Bank/Card/bKash/Nagad/Rocket/Upay/Other | `payment_method` seed | Payments | `tests/unit/test_payment_methods.py` | P |
| PAY-003 | Period views | `domain/period.py` | Payments | `tests/ui/test_payments_view.py` | P |
| PAY-004 | Accurate totals, no floats | integer paisa | Payments | `test_payment_service.py` | P |
| PAY-005 | Duplicate submission prevented | idempotency key + unique index | Payment dialog | `tests/unit/test_payment_idempotency.py` | P |

## FIN — Financial history
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| FIN-001 | Per-patient financial history | `repositories.finance` | Financial History | `tests/unit/test_financial_history.py` | P |
| FIN-002 | Consistent billed/paid/outstanding | single source module | profile/Accounting | `tests/integration/test_financial_consistency.py` | P |
| FIN-003 | No drift-prone editable totals | cache recomputed in-txn | — | consistency job test | P |

## STK — Inventory
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| STK-001 | Full item/purchase/batch/movement model | `inventory_*` tables | Inventory | `tests/unit/test_inventory_service.py` | P |
| STK-002 | Expiry monitoring + low-stock alerts | queries + notifications | Inventory/Notifications | `tests/unit/test_inventory_alerts.py` | P |
| STK-003 | History survives deactivation | soft delete, retained rows | Inventory | `test_inventory_service.py` | P |
| STK-004 | Auditable changes | audit entries on every movement | — | `tests/security/test_audit_entries.py` | P |
| STK-005 | Controlled stock updates | service-only mutation | Inventory | `test_inventory_service.py` | P |

## ACC — Accounting
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| ACC-001 | Income & expenses, configurable categories | `expense`, `expense_category`, `income` | Accounting | `tests/unit/test_accounting_service.py` | P |
| ACC-002 | Income from payments + other sources | `accounting_service` | Accounting | `test_accounting_service.py` | P |
| ACC-003 | Daily/monthly/yearly/custom reports | report queries | Accounting | `tests/unit/test_accounting_reports.py` | P |
| ACC-004 | Service-level financial permission | `finance.*`/`accounting.*` | Accounting | `tests/security/test_financial_isolation.py` | P |

## STF / USR — Staff & users
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| STF-001 | Staff fields | `staff` | Staff & Users | `tests/unit/test_staff_service.py` | P |
| STF-002 | Staff vs user separation | `user.staff_id` nullable | Staff & Users | `test_staff_service.py` | P |
| USR-001 | Admin creates users, assigns roles | `user_service`, `role_service` | Staff & Users | `tests/unit/test_user_service.py` | P |
| USR-002 | Deactivation preserves history | `user.is_active` | Staff & Users | `test_user_service.py` | P |
| USR-003 | Password reset/force change | `user_service` + audit | Staff & Users | `test_user_service.py` | P |

## RBAC / AUTH
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| RBAC-001 | Granular, data-driven roles | `role`, `role_permission` | Staff & Users | `tests/unit/test_rbac.py` | P |
| RBAC-002 | 40+ permission catalogue | `domain/permissions.py` | role editor | `tests/unit/test_permission_catalogue.py` | P |
| RBAC-003 | Enforcement at service layer | `@require` | — | `test_permission_matrix.py` | P |
| RBAC-004 | No bypass via screen/export/search | services only path | — | `test_financial_isolation.py` | P |
| RBAC-005 | Every service declares permission | decorator coverage test | — | `tests/security/test_decorator_coverage.py` | P |
| AUTH-001 | Argon2id, unique salts | `security/password.py` | Login | `tests/unit/test_password.py` | P |
| AUTH-002 | Correct login/logout, protected session | `security/session.py` | Login/header | `tests/unit/test_session.py` | P |
| AUTH-003 | Auto-lock 5/10/15/30 min | `LockOverlay` + activity monitor | shell | `tests/ui/test_auto_lock.py` | P |
| AUTH-004 | Auto-lock preserves work | draft autosave/restore | editors | `tests/ui/test_draft_persistence.py` | P |
| AUTH-005 | Unlock requires authentication | lock overlay | shell | `test_auto_lock.py` | P |
| AUTH-006 | Re-auth for sensitive ops | `ReAuthDialog` | danger flows | `tests/security/test_reauth.py` | P |
| AUTH-007 | Lockout + password policy | `security/password.py`, settings | Settings | `test_password.py` | P |

## ACT / BKP / SET / DST
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| ACT-001…005 | Offline activation, derived, honest docs | `security/activation.py`, docs | Activation dialog | `tests/unit/test_activation.py` + grep test for literal code | P |
| BKP-001…009 | Manual/auto backup, atomic, verified, restore semantics, pre-restore backup | `backup/*` | Backup & Restore | `tests/backup/*` | P |
| SET-001/002 | Central settings incl. danger zone | `settings_service`, `SettingsView` | Settings | `tests/ui/test_settings_view.py` | P |
| DST-001…003 | Safeguards: warnings, typed confirmation, re-auth, safety backup | `ui/dialogs/confirm_danger.py` | danger dialogs | `tests/ui/test_destructive_guards.py` | P |

## SRC / APT / QUE / NOT / DSH
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| SRC-001…003 | Global search, filters, permission-aware | `search_service` | header | `tests/unit/test_search_permissions.py` | P |
| APT-001…006 | Appointment states, both entry points, status history | `appointment*` | Appointments | `tests/unit/test_appointment_service.py` | P |
| QUE-001…004 | Queue states, live updates, clarity | `queue_service`, `QueueView` | Queue | `tests/ui/test_queue_view.py` | P |
| NOT-001…004 | Notification types, read state, permission filter | `notification*` | Notification drawer | `tests/unit/test_notifications.py` | P |
| DSH-001…004 | Dashboard widgets, grid, states, real data | `dashboard_service` | Dashboard | `tests/unit/test_dashboard_accuracy.py` | P |

## ATT / REF / AUD / DB / MON / MED
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| ATT-001…005 | Attachments: types, metadata, preview, validation, permissions | `attachment_service` | Attachments tab | `tests/unit/test_attachments.py` | P |
| REF-001/002 | Referral records + history | `referral` | Referrals/timeline | `tests/unit/test_referral_service.py` | P |
| AUD-001…003 | Audit coverage, fields, append-only | `audit_service` + triggers | Audit Log, System Health | `tests/integration/test_audit_append_only.py` | P |
| DB-001…006 | Entity coverage, FKs, deletion rules, migrations, integrity checks | `data/models`, Alembic | System Health | `tests/integration/test_schema_integrity.py` | P |
| MON-001…004 | Single source totals, decimal math, transactions | `domain/invoice_math`, UoW | — | `test_financial_consistency.py` | P |
| MED-001…004 | Clinical history preservation, chart history, actor identity, audited edits | services + insert-only rules | profile/chart | `tests/integration/test_clinical_history.py` | P |

## BNG / PPV / KBD / ERR / LOG / PER / STE
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| BNG-001…003 | Unicode everywhere, bundled fonts, realistic tests | fonts + tests | all | `tests/print/test_unicode_pdf.py`, `tests/unit/test_unicode.py` | P |
| PPV-001…004 | Preview parity, paper info, no clipping | `PrintPreviewDialog` | preview | `tests/ui/test_print_preview.py` | P |
| KBD-001…003 | Shortcut set, no conflicts, help | `ui/shortcuts.py` | all | `tests/ui/test_shortcuts.py` | P |
| ERR-001…003 | Central error hierarchy, excepthook, `ErrorDialog`, redacted logging | `core/errors.py`, `app.py`, `components/dialogs.py` | error dialog | `tests/unit/test_errors.py`, `tests/ui/test_components.py` | V |
| LOG-001…003 | Rotating structured logs, no secrets, diagnostics export | `core/logging_setup.py`, `diagnostics.py` | System Health | `tests/unit/test_logging.py`, `tests/ui/test_cli.py` | V |
| PER-001…003 | Paging/indexing/off-thread work | repos, workers | all | `tests/stress/*` | P |
| STE-001 | All states on every screen | `components/states.py` (`StateStack`) | all | `tests/ui/test_components.py` | V |

## IMP / RET / SEC / LIC / GIT / PR / REL / INS / CMT / STR / E2E / UAA / NBI / FFH / BKV / DCP / DRA / ABT / DCM / PHP / TRC / QBR / RBC
| REQ | Requirement | Impl | Screen | Test | Status |
|---|---|---|---|---|---|
| IMP-001…003 | CSV/XLSX import-export with validation & permissions | `import_export_service` | lists/Settings | `tests/unit/test_import_export.py` | P |
| RET-001/002 | Archive vs soft vs hard delete vs reset | services + guards | danger zone | `tests/integration/test_deletion_semantics.py` | P |
| SEC-001…006 | Secrets, logging, path safety, uploads, parameterised SQL, service-level checks | `core`, `security`, services | — | `tests/security/*` | P |
| LIC-001…003 | Dependency enumeration + notices + compatibility | `docs/15`, `THIRD_PARTY_NOTICES.md`, `licenses/` | About | CI `hygiene` job, `tests/ui/test_about_view.py` | I |
| GIT-001…004 | Branch/PR discipline + Actions gates (lint, type, tests Linux/Windows, dead code, hygiene) | `.github/workflows/ci.yml` | — | CI | V |
| PR-001 | Agent never merges | process | — | phase gate | P |
| REL-001/002 | No premature build; all gates | process | — | release checklist | P |
| INS-001…008 | Installer behaviour, data preservation, reinstall | Inno Setup | — | CI install/uninstall/reinstall | P |
| CMT-001 | Clean-machine checklist | `--selftest` + CI | — | Windows CI | P |
| STR-001/002 | Stress scenarios | fixtures | — | `tests/stress/*` | P |
| E2E-001 | Full clinic workflow | everything | all | `tests/e2e/test_full_workflow.py` | P |
| UAA-001/002 | Screen-by-screen audits | `ui/diagnostics.py`, `--audit-layout` | all | `tests/ui/test_layout_audit.py` + human screenshot review | IP |
| NBI-001/002 | Every interactive element works | component behaviour tests | all | `tests/ui/test_components.py` | IP |
| FFH-001 | File/folder error handling | `core/fileutil.py` (atomic write/copy, space check) | — | `tests/unit/test_fileutil.py` | V |
| BKV-001…003 | Backup verification & test restore | `backup/verify.py` | Backup & Restore | `tests/backup/test_verify.py` | P |
| DCP-001 | Corruption protection | transactions, safe writes | — | `tests/integration/test_crash_safety.py` | P |
| DRA-001/002 | Real numbers, independent verification | `dashboard_service` | Dashboard | `test_dashboard_accuracy.py` | P |
| ABT-001…004 | About: Dentiva Pro, Shohan Khan, email, notices | `src/dentiva/ui/views/about.py` | About | `tests/ui/test_about_view.py` | V |
| DCM-001/002 | Documentation matches implementation | `docs/*` | — | phase gate | P |
| PHP-001…003 | Phase protocol | process | — | phase reports | P |
| TRC-001 | Traceability matrix maintained every phase | this file | — | phase gate review | V |
| TRC-002 | Matrix cross-checked against the test suite | `tools/trace_report.py` (Phase 3) | — | CI | P |
| QBR-001/002 | Quality bar | everything | — | release gates | P |
| RBC-001 | Release-blocking conditions | release checklist | — | release gate | P |

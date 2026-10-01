# Dentiva Pro — Requirements Baseline (Phase 1)

- Document owner: Lead architect
- Version: 1.0 (Phase 1 freeze candidate)
- Date: 2026-10-01
- Product: **Dentiva Pro 1.0.0** — offline-first Windows desktop dental clinic management system
- Market: Bangladesh (English UI; Unicode/Bangla user content; currency BDT / ৳)

Every requirement below is derived from the master build specification. Each has a
stable ID used by `docs/12-requirements-traceability.md` and by the test suite
(`tests/**` reference REQ IDs in docstrings so coverage can be traced).

Legend — **M** mandatory (release-blocking), **S** should-have (implemented in v1),
**N** explicitly out of scope for v1 (recorded so the omission is a decision, not an
oversight).

---

## 1. General product requirements (GEN)

- **REQ-GEN-001 (M)** Product name is **Dentiva Pro**; About screen, window titles,
  installer, shortcuts and documents must all identify it as Dentiva Pro.
- **REQ-GEN-002 (M)** UI language is professional English.
- **REQ-GEN-003 (M)** All user-generated content (names, addresses, notes, clinical
  text, prescriptions, item names, medicine names, template labels) supports full
  Unicode incl. Bangla/Bengali, stored and rendered without corruption.
- **REQ-GEN-004 (M)** Currency is Bangladesh Taka, displayed as **৳** / **BDT**,
  configurable symbol/format in Settings.
- **REQ-GEN-005 (M)** Fully offline after installation + activation. No mandatory
  cloud service, SaaS, paid API/SDK, subscription, cloud DB or online backend.
- **REQ-GEN-006 (M)** No patient or clinic data is transmitted to external servers.
  No telemetry, no crash-phone-home, no update checker that requires internet.
- **REQ-GEN-007 (M)** Every third-party dependency is audited for licence,
  commercial redistribution, offline operation, security and version (Phase 1 + 18).
- **REQ-GEN-008 (M)** No artificial application-level limits on patients, visits,
  prescriptions, appointments, invoices, payments, attachments, inventory items or
  audit rows. Pagination is a performance tool, not a record cap.
- **REQ-GEN-009 (M)** No fake buttons, no placeholder screens, no mocked workflows,
  no demo/fake data in production paths, no dead code.
- **REQ-GEN-010 (M)** No TODO/FIXME related to unfinished product functionality in
  the production release (enforced by a CI grep gate; see REQ-GIT-006).
- **REQ-GEN-011 (M)** No broken navigation: every navigation item opens a real,
  working screen.
- **REQ-GEN-012 (M)** No intentionally disabled mandatory workflow.
- **REQ-GEN-013 (M)** No dead-code modules; enforced by `vulture`/ruff dead-code
  review in Phase 15–18.
- **REQ-GEN-014 (M)** Treated as **final production version 1.0.0**, not a demo.
- **REQ-GEN-015 (M)** Architecture must not be designed around future features as an
  excuse to leave current functionality incomplete.
- **REQ-GEN-016 (S)** Windows 10 (1809+) and Windows 11 (x64) supported.
- **REQ-GEN-017 (N)** Mobile/web client, multi-site sync, cloud backup, SMS/email
  gateway, online appointment booking, DICOM/PACS integration, imaging device
  capture, insurance/claim processing, payroll, multi-language UI.

## 2. Central business relationship & scale (BIZ)

- **REQ-BIZ-001 (M)** Patient → Appointment/Queue → Visit → Clinical Examination →
  Dental Chart → Treatment → Prescription → Invoice → Payment → Financial History →
  Referral → Follow-up Appointment → Longitudinal Timeline is modelled as connected,
  traceable data — never as disconnected records.
- **REQ-BIZ-002 (M)** Every clinical/operational/billing record is related to the
  correct patient, and where applicable to the correct visit, dentist, invoice,
  payment or appointment.
- **REQ-BIZ-003 (M)** Supports one or many dentists; every clinical action retains
  the identity of the dentist who performed or authored it.
- **REQ-BIZ-004 (M)** Unlimited patient records and unlimited per-patient history
  (visits, prescriptions, invoices, payments, attachments).

## 3. First-run experience & clinic setup (FRS)

- **REQ-FRS-001 (M)** First launch (no configured clinic) opens a professional
  first-run setup wizard, not an empty dashboard.
- **REQ-FRS-002 (M)** Wizard collects clinic/business identity: clinic name, logo,
  address, phone, additional contact info (email, website, emergency line).
- **REQ-FRS-003 (M)** Wizard configures **one or more dentists**, each with name,
  designation(s), qualification/certification(s), registration number, contact, and
  professional details.
- **REQ-FRS-004 (M)** A dentist supports **multiple designations** and **multiple
  qualifications/certifications** (normalised tables, not single text fields).
- **REQ-FRS-005 (M)** Wizard creates the initial administrative account: username +
  securely hashed password (Argon2id), with password policy enforcement.
- **REQ-FRS-006 (M)** Wizard configures default currency, clinic settings, document /
  printing defaults, backup configuration and security/session settings.
- **REQ-FRS-007 (M)** Setup is transactional and recoverable: interruption (crash,
  power loss, cancel) must not leave a partially initialised database. The wizard
  writes into a single DB transaction and only commits a complete, valid clinic
  profile; incomplete state is rolled back and setup restarts cleanly.
- **REQ-FRS-008 (M)** Production use is blocked while mandatory setup is incomplete.
- **REQ-FRS-009 (S)** Wizard steps: Clinic → Dentists → Staff/Users (optional) →
  Preferences (currency/print/backup/security) → Review & Finish, with per-step
  validation, back/next, and a review summary.
- **REQ-FRS-010 (M)** Logo upload validated (type/size), stored in managed assets
  and used by documents.

## 4. Application shell (SHL)

- **REQ-SHL-001 (M)** Professional Windows desktop shell (own window chrome, app
  icon, min/max/close, proper window state persistence).
- **REQ-SHL-002 (M)** Global header contains: Dentiva Pro identity/logo, configured
  clinic name, current date, notification centre, and user/session info (user name,
  role, lock/logout/menu).
- **REQ-SHL-003 (M)** Left sidebar is collapsible; expanded and collapsed states are
  both fully functional (icons + tooltips when collapsed).
- **REQ-SHL-004 (M)** Sidebar primary structure, grouped exactly as:
  - **Practice**: Dashboard, Patients, Appointments, Queue
  - **Clinical**: Treatments, Prescriptions
  - **Billing**: Invoice, Payments, Inventory, Accounting
  - **Administration**: Staff & Users, Backup & Restore, Settings, About
- **REQ-SHL-005 (S)** Additional justified system utilities: **Audit Log**,
  **System Health** (Administration group); **Global Search** and **Notifications**
  in the header; **Print Center** reachable from every printable document.
- **REQ-SHL-006 (M)** Sidebar state persists across sessions (width, collapsed, last
  visited screen where sensible).
- **REQ-SHL-007 (M)** Every navigation item leads to a real working screen.
- **REQ-SHL-008 (M)** No decorative-only navigation item.
- **REQ-SHL-009 (S)** Breadcrumb / screen title area and contextual actions per
  screen.

## 5. Premium UI/UX system (UIX)

- **REQ-UIX-001 (M)** Flagship premium clinical design language communicating
  healthcare, modern dentistry, precision, trust, cleanliness, technology, clarity
  and premium commercial quality.
- **REQ-UIX-002 (M)** Must not look like a generic Python application; no raw
  default framework controls without visual integration.
- **REQ-UIX-003 (M)** A coherent design system with: typography, spacing, colour
  tokens, elevation, border radius, iconography, buttons, inputs, cards, tables,
  tabs, dialogs, drawers, menus, tooltips, badges, status indicators, notifications,
  loading, error, empty, success, disabled, focus, hover, pressed, selected,
  validation and destructive states.
- **REQ-UIX-004 (M)** Consistent spacing and alignment; text never overflows its
  container; icons optically centred; icon+text inside buttons/tabs perfectly
  aligned.
- **REQ-UIX-005 (M)** No clipped labels, no overlapping components, no accidental
  horizontal overflow, no broken vertical scrolling, no content unreachable below
  the viewport, nothing disappearing on resize.
- **REQ-UIX-006 (M)** No visually-present-but-inactive buttons or tabs.
- **REQ-UIX-007 (S)** Subtle, purposeful, smooth, performance-conscious animations
  for navigation, dialogs, panels, notifications, loading and interactive states.
- **REQ-UIX-008 (M)** Every screen defines loading, empty, error, success, disabled,
  no-permission and validation states.
- **REQ-UIX-009 (M)** Design tokens live in one Python module and generate QSS; no
  hard-coded colours scattered through widgets.

## 6. Responsive desktop & High-DPI (RSP)

- **REQ-RSP-001 (M)** Verified at 1366×768, 1920×1080, 2560×1440, 3840×2160.
- **REQ-RSP-002 (M)** Verified at Windows scaling 100 %, 125 %, 150 %, 175 %, 200 %
  (175 %/200 % validated on the Windows runner + manual matrix; see `docs/10`).
- **REQ-RSP-003 (M)** Usable at the smallest supported desktop resolution
  (1366×768) without unusable truncation.
- **REQ-RSP-004 (M)** Responsiveness is achieved by layout rules (breakpoints,
  size policies, stretch factors), not by "allow scrolling everywhere".
- **REQ-RSP-005 (M)** Deliberate responsive card grid: at a 3-column breakpoint a
  six-card layout renders **3+3**, never 4+2 or 5+1 (see `ResponsiveGrid` in
  `docs/07`).
- **REQ-RSP-006 (M)** Every screen is reviewed at multiple window sizes
  (automated geometry audit + human screenshot review).

## 7. Icon & branding (ICO)

- **REQ-ICO-001 (M)** Professional Dentiva Pro icon concept combining dental/clinical
  identity with premium modern technology.
- **REQ-ICO-002 (M)** Transparent background and transparent corners; subject
  optically centred (not merely mathematically), with proper padding.
- **REQ-ICO-003 (M)** No unwanted background rectangle, no accidental white/coloured
  corners, no poor cropping, no stretching/distortion.
- **REQ-ICO-004 (M)** A real multi-resolution Windows `.ico` (16, 20, 24, 32, 40,
  48, 64, 96, 128, 256) is generated from a master PNG — not a renamed PNG.
- **REQ-ICO-005 (M)** Icon appears correctly in: executable, installer, Start Menu,
  desktop shortcut, taskbar and application window title bar.
- **REQ-ICO-006 (S)** Master PNG also used in About screen and print headers.

## 8. Patient management (PAT)

- **REQ-PAT-001 (M)** Unlimited patients.
- **REQ-PAT-002 (M)** Patient list filters: Today, 7 days, 30 days, 90 days, 1 year,
  All, and a Custom range.
- **REQ-PAT-003 (M)** Default ordering surfaces newly registered / recently updated
  patients first (Today's records naturally first).
- **REQ-PAT-004 (M)** Registration form contains at minimum: patient code/ID, name,
  date of birth and/or age, gender, blood group, address, primary phone, emergency
  contact, presenting problem/complaint, past medical/dental history, notes, plus
  architecturally justified extras (guardian name, occupation, NID/passport,
  email, referred-by, marital status, preferred language, tags, photo, city/area,
  postal code, first-visit date).
- **REQ-PAT-005 (M)** Form is organised into logical sections/tabs/progressive
  disclosure — not one unusable giant page.
- **REQ-PAT-006 (M)** Patient code is unique and validated (auto-generated pattern
  configurable in Settings, manual override allowed with uniqueness check).
- **REQ-PAT-007 (M)** Duplicate detection signals before creation: phone, name+DOB,
  name similarity, emergency contact overlap; results shown as candidates.
- **REQ-PAT-008 (M)** Duplicate detection never silently merges patients; any merge
  is an explicit, audited, admin-permitted operation.
- **REQ-PAT-009 (M)** Patient list is paginated/virtualised with search, sort and
  filter; performance remains acceptable with large datasets.
- **REQ-PAT-010 (M)** Patient CRUD operations are permission-controlled.

## 9. Patient profile (PRF)

- **REQ-PRF-001 (M)** Clicking a patient opens a permanent professional profile.
- **REQ-PRF-002 (M)** Profile sections/tabs: Overview, Personal Information,
  Clinical Timeline, Visits, Dental Chart, Treatments, Prescriptions, Appointments,
  Invoices, Payments, Financial History, Referrals, Attachments.
- **REQ-PRF-003 (M)** Profile shows recent activity, visit count, previous
  treatments, prescription history, invoice & payment history.
- **REQ-PRF-004 (M)** Profile shows total billed, total paid, outstanding balance,
  and when outstanding amounts were later paid (linked to the settling payments).
- **REQ-PRF-005 (M)** Profile shows referral history and future appointments.
- **REQ-PRF-006 (M)** Profile actions (permission-gated): New Visit, New
  Appointment, New Prescription, New Invoice, Receive Payment.
- **REQ-PRF-007 (M)** Actions initiated from the profile inherit patient context —
  the user never re-selects the patient.
- **REQ-PRF-008 (S)** Profile header: photo/avatar, code, age/gender, phone, tags,
  alerts (allergies, outstanding balance, upcoming appointment).

## 10. Visits (VIS)

- **REQ-VIS-001 (M)** A patient can visit repeatedly; every visit is a separate,
  preserved historical clinical event.
- **REQ-VIS-002 (M)** Visit captures: date/time, attending dentist, reason, chief
  complaint, clinical findings, examination, diagnosis/assessment, dental chart
  findings, treatments performed, prescription, clinical notes, follow-up advice,
  referral, attachments, invoice relationship, payment relationship, next
  appointment.
- **REQ-VIS-003 (M)** Historical visits are never overwritten by later visits.
- **REQ-VIS-004 (M)** Editing a previous record is controlled (permission) and
  audited (before/after).
- **REQ-VIS-005 (S)** Visit status lifecycle (Open → In progress → Completed →
  Cancelled) with audit entries.

## 11. Clinical timeline (TML)

- **REQ-TML-001 (M)** Chronological per-patient timeline derived from real records:
  Registration, Visit, Clinical Examination, Dental Chart Update, Treatment,
  Prescription, Appointment, Invoice, Payment, Referral, Attachment, Note, Status
  change.
- **REQ-TML-002 (M)** Each entry shows date/time, event type, responsible
  dentist/staff and a summary.
- **REQ-TML-003 (M)** Easy to scan (grouping, filters by event type) and navigable
  into the underlying record.
- **REQ-TML-004 (M)** Timeline stays performant for very large histories
  (incremental/paged loading).

## 12. Dental chart (CHT)

- **REQ-CHT-001 (M)** Advanced interactive dental chart (painted widget, not a
  static decorative image).
- **REQ-CHT-002 (M)** Adult and paediatric dentition with documented tooth
  numbering (**FDI/ISO 3950**; Palmer/Universal label toggles) — see ADR-0010.
- **REQ-CHT-003 (M)** Single and multiple tooth selection.
- **REQ-CHT-004 (M)** Findings associated with the tooth (and surfaces) and the
  relevant visit.
- **REQ-CHT-005 (M)** Historical state preserved: a current change never erases
  knowledge of previous findings; "state as of visit" reconstruction.
- **REQ-CHT-006 (M)** Clear visual distinction of normal / affected / treated /
  missing / impacted / other supported statuses (configurable status catalogue with
  colour + legend).
- **REQ-CHT-007 (M)** Usable at different screen sizes; never clipped or overlapping.

## 13. Treatment catalog (TRT)

- **REQ-TRT-001 (M)** Structured, configurable treatment catalog: name, category,
  default price, active/inactive, notes, code, duration, tax-like/other attributes
  as justified.
- **REQ-TRT-002 (M)** Prices are **not** hard-coded anywhere in the application.
- **REQ-TRT-003 (M)** Administrator can modify the catalog at runtime.
- **REQ-TRT-004 (M)** Historical invoices keep the actual charged price at billing
  time (price snapshot on the invoice line), unaffected by later catalog changes.

## 14. Prescriptions (PRX)

- **REQ-PRX-001 (M)** Prescription creation from the patient profile **and** from
  the main Prescriptions section; patient and dentist selectable.
- **REQ-PRX-002 (M)** Multiple medicines per prescription.
- **REQ-PRX-003 (M)** Medicine fields: name, form (tablet/capsule/syrup/cream/
  drop/injection/ointment/other), strength, dose, frequency, schedule
  (Morning/Noon/Night or custom), before/after meal, duration, quantity,
  instructions, PRN/as-needed flag.
- **REQ-PRX-004 (M)** Structured fields plus free-text clinical instruction — no
  rigid format that blocks clinical expression.
- **REQ-PRX-005 (M)** Prescription identifies the prescribing dentist with
  designations and qualifications.
- **REQ-PRX-006 (S)** Medicine history/autocomplete from previously used medicines
  (configurable catalog), dosage templates.
- **REQ-PRX-007 (M)** Permission-controlled view/create/edit/print.

## 15. Clinical complaints & examination options (CLN)

- **REQ-CLN-001 (M)** Selectable structured options for common complaints and
  examination findings (pain, G. caries, swelling, gum bleeding, bad breath,
  sensitivity, caries, BDR/BDC, gingivitis, periodontal pocket, periodontitis,
  pulpitis, impacted teeth, dry socket, attrition/erosion, and similar).
- **REQ-CLN-002 (M)** Options are selectable (no repetitive manual typing).
- **REQ-CLN-003 (M)** Doctors can add custom/free-text clinical information.
- **REQ-CLN-004 (M)** The vocabulary is a configurable catalog (add/edit/deactivate)
  — not hard-coded and not limited to the example list.

## 16. Prescription document design (DOC)

- **REQ-DOC-001 (M)** Ultra-premium rich clinical document.
- **REQ-DOC-002 (M)** Header: clinic/dental care name, logo, address, phone,
  attending dentist name, designation(s), certification(s), qualification(s).
- **REQ-DOC-003 (M)** Patient section: name, gender, age/DOB, date, patient code,
  and other relevant info.
- **REQ-DOC-004 (M)** Clinical section supporting C/C, O/E, R/E/Advice (or an
  equivalent, well-designed structure).
- **REQ-DOC-005 (M)** Medicine area presents multiple medicines clearly without
  overlap.
- **REQ-DOC-006 (S)** Footer with configured clinic message / visiting information.
- **REQ-DOC-007 (M)** Bottom-right blank signature area for manual signing; no
  printed text inside the physical signature writing area.
- **REQ-DOC-008 (M)** Suitable for printing **and** PDF generation.
- **REQ-DOC-009 (M)** Long content is safe: long medicine lists paginate/flow, long
  notes wrap, nothing is clipped.

## 17. Printing & document engine (PRT)

- **REQ-PRT-001 (M)** Reusable architecture: Document Model → Layout Engine → Paper
  Profile → Print Preview → Printer Selection → Output. No hard-coded screenshots.
- **REQ-PRT-002 (M)** Paper profiles: A4, A5, 58 mm thermal, 80 mm thermal,
  mini/receipt, and configurable custom profiles.
- **REQ-PRT-003 (M)** Works with Windows-installed printers: USB, network, wireless,
  Bluetooth-paired Windows printers, thermal printers — anything exposed through
  Windows printing.
- **REQ-PRT-004 (M)** No proprietary paid printer SDK (standard Windows printing
  only).
- **REQ-PRT-005 (M)** Paper-size changes never cause overlap, clipping, broken
  alignment or missing data.
- **REQ-PRT-006 (M)** Print preview for every major printable document.
- **REQ-PRT-007 (M)** Printer selection (native print dialog + application printer
  profiles).
- **REQ-PRT-008 (M)** Save/print to PDF (application PDF generation **and** the
  standard Windows "print to PDF" workflow).
- **REQ-PRT-009 (M)** PDF preserves Unicode/Bengali (embedded font subsets).
- **REQ-PRT-010 (M)** High-DPI rendering stays sharp (vector text, 300 dpi
  rasterisation where rasterised).
- **REQ-PRT-011 (S)** Print Center: unified list of documents, reprint, PDF export,
  per-document paper profile memory.

## 18. Invoices (INV)

- **REQ-INV-001 (M)** Professional invoice design consistent with clinic branding:
  clinic name, logo, address, phone/contact.
- **REQ-INV-002 (M)** No dentist signature on the invoice by default (configurable
  off; not a baseline requirement).
- **REQ-INV-003 (M)** Line items: treatment/service, description, quantity, unit
  price, discount, line total.
- **REQ-INV-004 (M)** Totals: subtotal, discount, total, paid, due, payment status.
- **REQ-INV-005 (M)** Supports full payment, partial payment, no payment and later
  payment.
- **REQ-INV-006 (M)** Historical payments remain linked to the correct invoice.
- **REQ-INV-007 (M)** Prints correctly on A4, A5, thermal, mini and custom formats;
  long item lists flow safely.
- **REQ-INV-008 (M)** Invoice numbering configurable, unique, sequential, atomic.
- **REQ-INV-009 (M)** Voiding is permission-controlled, audited, and never destroys
  the financial record (void keeps the row, marks status, reverses accounting).

## 19. Payments (PAY)

- **REQ-PAY-001 (M)** Complete payment ledger: patient, invoice, amount, date/time,
  method, reference/transaction number, received by, notes, status.
- **REQ-PAY-002 (M)** Methods: Cash, Bank, Card, bKash, Nagad, Rocket, Upay, Other
  (configurable list).
- **REQ-PAY-003 (M)** Period views: today (default where appropriate), 7 days,
  30 days, 90 days, 1 year, custom, all-time.
- **REQ-PAY-004 (M)** Accurate totals; no floats (integer minor units).
- **REQ-PAY-005 (M)** Duplicate payment submission prevented (idempotency key per
  payment dialog + unique constraint on (invoice, reference, amount, method, time)
  where a reference exists).

## 20. Financial history (FIN)

- **REQ-FIN-001 (M)** Per-patient financial history: invoices, payments, outstanding
  balances, payment dates, methods, adjustments.
- **REQ-FIN-002 (M)** Total billed / total paid / total outstanding derive
  consistently from authoritative transactional data.
- **REQ-FIN-003 (M)** No independently editable "total due" fields that can drift
  (denormalised caches are recomputed inside the same transaction and verified by
  an integrity job).

## 21. Inventory (STK)

- **REQ-STK-001 (M)** Inventory for dental supplies/accessories: item, category,
  supplier, purchase source, purchase date, batch/lot, quantity purchased, current
  stock, unit cost, expiry date, low-stock threshold, stock movement, adjustment,
  usage, notes.
- **REQ-STK-002 (M)** Expiry monitoring + low-stock alerts.
- **REQ-STK-003 (M)** Historical purchase and stock-movement records survive
  deactivation of the item.
- **REQ-STK-004 (M)** Inventory changes are auditable.
- **REQ-STK-005 (M)** Stock changes only through controlled business logic (no
  direct editable stock field in the UI).

## 22. Accounting (ACC)

- **REQ-ACC-001 (M)** Income and expense records; expense categories configurable
  (rent, electricity, internet, accessories/supplies, staff salary, maintenance,
  other operating expenses, custom).
- **REQ-ACC-002 (M)** Income derived from payments and other configured sources.
- **REQ-ACC-003 (M)** Daily, monthly, yearly and custom-period reports with
  meaningful totals and summaries.
- **REQ-ACC-004 (M)** Financial data hidden from unauthorised roles, enforced in the
  service layer (not only in the UI).

## 23. Staff (STF)

- **REQ-STF-001 (M)** Staff records: name, DOB/age, address, blood group,
  identification number, photo, phone, role/department, salary, joining
  information, status, notes.
- **REQ-STF-002 (M)** Staff and Users are conceptually separated: a staff member
  need not have a login; a login references the relevant staff/dentist entity where
  applicable.

## 24. Users (USR)

- **REQ-USR-001 (M)** Administrator creates users, assigns roles, configures
  permissions.
- **REQ-USR-002 (M)** Users can be activated/deactivated; deactivation preserves
  history and audit references.
- **REQ-USR-003 (M)** Force password change / admin password reset with audit.

## 25. RBAC & access control (RBAC)

- **REQ-RBAC-001 (M)** Granular RBAC; not limited to a few hard-coded roles. Roles
  are data (DB), editable by the administrator.
- **REQ-RBAC-002 (M)** Permission catalogue includes at least: patient
  view/create/edit/delete, visit view/create/edit, prescription
  view/create/edit/print, appointment view/create/edit/delete, queue management,
  treatment management, invoice view/create/edit/void, payment view/create/edit,
  financial reports, inventory management, accounting management, staff management,
  user management, settings management, backup creation, backup restore, audit log
  viewing, data export, data deletion, business deletion (full catalogue in
  `docs/06`).
- **REQ-RBAC-003 (M)** Permissions enforced at business-logic/service level; UI
  hiding is not security.
- **REQ-RBAC-004 (M)** A user without financial permission cannot obtain financial
  data through any alternative screen, shortcut, export, report, search result or
  direct business operation.
- **REQ-RBAC-005 (M)** Every service method declares its required permission; a
  single decorator/middleware enforces it (audit-friendly, testable without UI).

## 26. Authentication & password security (AUTH)

- **REQ-AUTH-001 (M)** No plaintext passwords; Argon2id with unique salts.
- **REQ-AUTH-002 (M)** Login/logout implemented correctly; session state protected.
- **REQ-AUTH-003 (M)** Session timeout with auto-lock at a configurable
  **5 / 10 / 15 / 30 minutes**.
- **REQ-AUTH-004 (M)** Auto-lock must not destroy unsaved work (editor drafts
  persisted and restored on unlock).
- **REQ-AUTH-005 (M)** Unlock requires re-authentication (password of the logged-in
  user).
- **REQ-AUTH-006 (M)** Sensitive administrative/destructive operations require
  re-authentication.
- **REQ-AUTH-007 (S)** Failed-login throttling/lockout and password policy
  (length, complexity, reuse) configurable.

## 27. Activation (ACT)

- **REQ-ACT-001 (M)** One-time activation with the code `1516591935015165`.
- **REQ-ACT-002 (M)** The code is never stored as a plainly readable string in
  source; a secure derived representation + verification is used (ADR-0006).
- **REQ-ACT-003 (M)** Activation is fully offline; no online activation.
- **REQ-ACT-004 (M)** After activation the application runs with no internet.
- **REQ-ACT-005 (M)** Documentation states honestly that a purely local fixed code
  cannot be made impossible to reverse engineer; the goal is reasonable offline
  tamper resistance.

## 28. Backup & restore (BKP)

- **REQ-BKP-001 (M)** Manual backup with native folder selection (no manual path
  typing).
- **REQ-BKP-002 (M)** Backup filenames contain date/time.
- **REQ-BKP-003 (M)** Backup is atomic (temp file + final rename); incomplete
  backups are never presented as valid.
- **REQ-BKP-004 (M)** Backup verification (checksums + SQLite integrity check on
  the restored copy).
- **REQ-BKP-005 (M)** Automatic backup scheduling at configurable 7 / 15 / 30-day
  intervals (and custom), fully offline.
- **REQ-BKP-006 (M)** Restore lets the user select backup files; multi-selection
  semantics are defined and stated (newest valid full backup is restored; backups
  are never merged).
- **REQ-BKP-007 (M)** Automatic pre-restore backup of the current live state.
- **REQ-BKP-008 (M)** Restore validates integrity before replacing live data; on
  failure the live database is left untouched.
- **REQ-BKP-009 (M)** Recovery behaviour documented and tested (interrupted
  restore, corrupted archive, missing attachments, low disk space).

## 29. Settings (SET)

- **REQ-SET-001 (M)** Centralised, professionally organised settings covering:
  clinic information, logo, dentists, designations, qualifications, contact
  information, printer profiles, paper sizes, currency, date/time formatting,
  prescription settings, invoice settings, clinical option catalogs, treatment
  catalog, medicine/catalog settings, notification settings, backup settings,
  security/session timeout, user/role settings, and other system configuration.
- **REQ-SET-002 (M)** Settings clearly distinguish safe configuration changes from
  destructive actions (separate "Danger zone" area).

## 30. Destructive action safeguards (DST)

- **REQ-DST-001 (M)** Destructive operations (delete patient, delete records,
  delete all records, restore backup, delete business, reset application) require
  authorisation, clear warnings, an explanation of consequences, typed confirmation
  where appropriate, and administrator re-authentication where appropriate.
- **REQ-DST-002 (M)** A safety backup is created before destructive operations
  where feasible.
- **REQ-DST-003 (M)** Destructive consequences are never hidden.

## 31. Global search (SRC)

- **REQ-SRC-001 (M)** Global search across patients, patient codes, phone numbers,
  visits, prescriptions, appointments, invoices, payments, inventory, staff and
  other appropriate records.
- **REQ-SRC-002 (M)** Filtering and meaningful, grouped results.
- **REQ-SRC-003 (M)** Search respects permissions: an unauthorised user cannot
  discover restricted financial or administrative records through search.

## 32. Appointments (APT)

- **REQ-APT-001 (M)** Upcoming and historical appointments.
- **REQ-APT-002 (M)** States: Scheduled, Confirmed, Arrived, Completed,
  Missed/No-show, Cancelled, Rescheduled (plus justified extras).
- **REQ-APT-003 (M)** Creation from the Appointments section and from a patient
  profile.
- **REQ-APT-004 (M)** Links to patient and (where applicable) dentist.
- **REQ-APT-005 (M)** Historical status preserved (status history table).
- **REQ-APT-006 (S)** Rescheduling flow, reminders surfaced in the notification
  centre, day/week views.

## 33. Queue (QUE)

- **REQ-QUE-001 (M)** Queue states: Waiting, Called, In consultation, Completed,
  Skipped, Cancelled.
- **REQ-QUE-002 (M)** Authorised staff manage queue state.
- **REQ-QUE-003 (M)** Queue updates efficiently without unnecessary full-screen
  reloads.
- **REQ-QUE-004 (M)** Current queue state immediately understandable (now serving,
  waiting count, next, waiting time).

## 34. Notification centre (NOT)

- **REQ-NOT-001 (M)** Notification types: upcoming appointments, missed
  appointments, outstanding payments, low stock, expiring inventory, backup
  success/failure, security events, system warnings.
- **REQ-NOT-002 (M)** Read/unread status.
- **REQ-NOT-003 (M)** Notifications respect permissions and user context.
- **REQ-NOT-004 (M)** No meaningless decorative notifications.

## 35. Dashboard (DSH)

- **REQ-DSH-001 (M)** Operational command centre with widgets: today's patients,
  today's appointments, queue, completed visits, pending appointments, today's
  revenue, outstanding dues, low stock, expiring inventory, recent patients, recent
  payments, upcoming appointments, clinical activity, quick actions.
- **REQ-DSH-002 (M)** Deliberate responsive grid — no accidental wrapping.
- **REQ-DSH-003 (M)** Designed empty, loading and error states.
- **REQ-DSH-004 (M)** All numbers come from real database/business services — never
  hard-coded demo values.

## 36. Attachments (ATT)

- **REQ-ATT-001 (M)** Per-patient attachments: PDF, images, documents and carefully
  selected safe formats.
- **REQ-ATT-002 (M)** Metadata: filename, type, size, date/time, uploaded by,
  description/category, patient relationship.
- **REQ-ATT-003 (M)** Direct preview where technically possible (PDF/images).
- **REQ-ATT-004 (M)** Validation of type and size; corrupted files rejected; upload
  errors handled gracefully; missing file on disk handled without crashing.
- **REQ-ATT-005 (M)** Permission-controlled access.

## 37. Referrals (REF)

- **REQ-REF-001 (M)** Referral records: date, referring dentist, destination
  doctor/provider, reason, notes, status, follow-up information.
- **REQ-REF-002 (M)** Referral history visible in patient profile and timeline.

## 38. Audit log (AUD)

- **REQ-AUD-001 (M)** Audit covers: login, logout, patient create/edit/delete,
  clinical record changes, prescription create/edit, invoice create/edit/void,
  payment create/edit, inventory changes, accounting changes, user creation, role
  changes, permission changes, settings changes, backup creation, restore
  operations, destructive operations, and other security-sensitive actions.
- **REQ-AUD-002 (M)** Audit fields: timestamp, user, action, entity, entity id,
  summary, and before/after for sensitive changes where feasible.
- **REQ-AUD-003 (M)** Normal users cannot erase audit history (append-only,
  DB-enforced).

## 39. Data model & DB integrity (DB)

- **REQ-DB-001 (M)** Relational model covering: Clinic/Business, Users, Roles,
  Permissions, Staff, Dentists, Patients, Patient Attachments, Visits, Clinical
  Findings, Dental Charts, Tooth Findings, Treatments, Treatment Catalog,
  Prescriptions, Prescription Items, Appointments, Queue Entries, Invoices, Invoice
  Items, Payments, Payment Methods, Inventory Items, Suppliers, Purchases, Stock
  Movements, Expenses, Income, Referrals, Notifications, Audit Logs, Backups,
  Printer Profiles, Settings (+ more as designed in `docs/04`).
- **REQ-DB-002 (M)** Proper PK/FK, no orphan records, deliberate deletion/archival
  behaviour.
- **REQ-DB-003 (M)** Deleting a parent record never corrupts historical financial or
  clinical relationships (restrict/soft-delete + audit).
- **REQ-DB-004 (M)** Migrations used for all schema changes.
- **REQ-DB-005 (M)** Integrity checks (`PRAGMA integrity_check`/`foreign_key_check`)
  exposed in System Health and run before/after backup & restore.
- **REQ-DB-006 (M)** Transactions for all multi-step operations; no unsafe sequence
  of multi-table financial/clinical updates.

## 40. Financial data integrity (MON)

- **REQ-MON-001 (M)** No independent duplicate calculation of important totals; one
  authoritative source per figure.
- **REQ-MON-002 (M)** Invoice total, payments, outstanding, refunds, discounts and
  accounting summaries remain mathematically consistent.
- **REQ-MON-003 (M)** Decimal/integer money arithmetic only.
- **REQ-MON-004 (M)** Transactions + safe rollback.

## 41. Medical data integrity (MED)

- **REQ-MED-001 (M)** Historical clinical information never disappears because a
  later visit occurs.
- **REQ-MED-002 (M)** Current dental chart state never overwrites a previous visit's
  chart state.
- **REQ-MED-003 (M)** Clinical records retain responsible dentist/user identity.
- **REQ-MED-004 (M)** Edits to sensitive historical records are controlled and
  audited.

## 42. Bengali / Unicode (BNG)

- **REQ-BNG-001 (M)** Unicode everywhere: forms, tables, profiles, prescriptions,
  invoices, PDF, print preview, printed output.
- **REQ-BNG-002 (M)** No assumption that a specific font exists on the target
  Windows system (bundled OFL fonts — ADR-0011).
- **REQ-BNG-003 (M)** Tested with realistic Bangla clinic/patient content and mixed
  English+Bangla content.

## 43. Print preview (PPV)

- **REQ-PPV-001 (M)** Print preview for every major printable document.
- **REQ-PPV-002 (M)** Preview matches actual output as closely as the rendering
  architecture permits (single layout engine — ADR-0004).
- **REQ-PPV-003 (M)** Printer/paper profile selectable; paper size clearly
  displayed.
- **REQ-PPV-004 (M)** Preview never shows clipped content; multi-page navigation.

## 44. Keyboard shortcuts (KBD)

- **REQ-KBD-001 (M)** Professional shortcuts for: global search, new patient, save,
  cancel, print, new appointment, new visit, navigation, lock, refresh, close tab.
- **REQ-KBD-002 (M)** No conflicts with standard Windows behaviour without
  justification (documented mapping in `docs/07`).
- **REQ-KBD-003 (S)** In-app shortcut help overlay.

## 45. Error handling (ERR)

- **REQ-ERR-001 (M)** Centralised error handling; recoverable errors produce useful
  user-facing messages.
- **REQ-ERR-002 (M)** No raw stack traces shown to ordinary users (details available
  via "Copy details"/logs).
- **REQ-ERR-003 (M)** Critical failures logged; unexpected errors never corrupt the
  database.
- **REQ-ERR-004 (M)** No crash caused by normal invalid user input.

## 46. Logging & diagnostics (LOG)

- **REQ-LOG-001 (M)** Structured application logging with rotation/retention.
- **REQ-LOG-002 (M)** No passwords or authentication secrets in logs; patient data
  minimised (IDs, not clinical content).
- **REQ-LOG-003 (S)** Diagnostics export bundle (logs + config summary + integrity
  report) from System Health.

## 47. Performance (PER)

- **REQ-PER-001 (M)** Responsive under realistic clinic workloads: pagination, lazy
  loading, indexing, incremental timeline loading.
- **REQ-PER-002 (M)** No long-running DB/file work on the UI thread where avoidable
  (ADR-0012).
- **REQ-PER-003 (M)** Search stays usable with large datasets; timelines stay usable
  for patients with very large histories.

## 48. States (STE)

- **REQ-STE-001 (M)** Every major screen/component defines loading, empty, error,
  success, disabled, no-permission and validation states; no blank white areas that
  look broken.

## 49. Import & export (IMP)

- **REQ-IMP-001 (S)** Controlled CSV import for patients (and structured catalogs)
  with preview, validation, duplicate detection, error report and permission
  enforcement.
- **REQ-IMP-002 (S)** CSV/XLSX export for patients, invoices, payments, inventory,
  expenses and audit (permission-gated; sensitive exports restricted).
- **REQ-IMP-003 (M)** Import cannot corrupt relational integrity (transactional +
  validated); export respects permissions.

## 50. Data retention & deletion (RET)

- **REQ-RET-001 (M)** Clear distinction between archive, soft delete, hard delete
  and destructive reset.
- **REQ-RET-002 (M)** Clinical/financial records are not casually hard-deleted where
  that would compromise auditability or referential integrity; where hard deletion
  is permitted it is authorised and safeguarded.

## 51. Security (SEC)

- **REQ-SEC-001 (M)** Passwords and sensitive configuration protected; no secrets,
  credentials or keys hard-coded.
- **REQ-SEC-002 (M)** No passwords in logs.
- **REQ-SEC-003 (M)** File paths validated; path traversal prevented for
  user-controlled filenames.
- **REQ-SEC-004 (M)** Uploaded file types validated; no execution of user-supplied
  files.
- **REQ-SEC-005 (M)** Parameterised/ORM-safe queries only; no unsafe dynamic SQL;
  no unsafe deserialisation.
- **REQ-SEC-006 (M)** UI-level permission checks are never the only control.

## 52. Dependency & licence audit (LIC)

- **REQ-LIC-001 (M)** Enumerate production dependencies with licence, version,
  purpose, redistribution compatibility, security and offline capability.
- **REQ-LIC-002 (M)** Include third-party notices where legally required
  (`THIRD_PARTY_NOTICES.md`, shipped in the installer and About screen).
- **REQ-LIC-003 (M)** No dependency with a licence incompatible with commercial
  distribution.

## 53. GitHub workflow (GIT)

- **REQ-GIT-001 (M)** Disciplined Git workflow on the connected repository.
- **REQ-GIT-002 (M)** Pull Requests used for meaningful changes.
- **REQ-GIT-003 (M)** GitHub Actions perform lint, formatting, type checks, unit
  tests, integration tests, build validation and packaging validation.
- **REQ-GIT-004 (M)** Final `.exe` produced by a reproducible release workflow.
- **REQ-GIT-005 (M)** Final executable published via GitHub Release; fallback is the
  repository `dist/` directory.
- **REQ-GIT-006 (S)** CI gate rejects TODO/FIXME markers tied to unfinished
  functionality and fails on dead-code findings in production modules.

## 54. PR merge rule (PR)

- **REQ-PR-001 (M)** The agent never merges a Pull Request. It may create, update,
  review and report readiness; the user merges.

## 55. Release build rule (REL)

- **REQ-REL-001 (M)** No final production `.exe` until all mandatory implementation,
  testing, audit, security, UI, printing, backup/restore, installer and release
  checks pass.
- **REQ-REL-002 (M)** Pre-build gates: requirements, architecture, database,
  relationship/integrity, RBAC, security, UI, UX, accessibility/usability, print,
  PDF, backup/restore, performance, stress, dependency/licence, code quality,
  dead-code, TODO, error-state, installer, uninstaller, clean-machine, end-to-end,
  regression, GitHub Actions and final verification audits.

## 56. Installer (INS)

- **REQ-INS-001 (M)** Installs correctly on a clean supported Windows environment.
- **REQ-INS-002 (M)** Creates required directories safely; installs files and
  dependencies.
- **REQ-INS-003 (M)** Creates Start Menu (and optional desktop) shortcuts with the
  Dentiva Pro icon.
- **REQ-INS-004 (M)** Starts the application after install; first-run setup and
  activation work.
- **REQ-INS-005 (M)** Provides a working uninstaller.
- **REQ-INS-006 (M)** Normal uninstall does not delete clinic data unless
  explicitly selected with a clear warning.
- **REQ-INS-007 (M)** Reinstall/upgrade handled without breaking the installation
  state; migrations run on first launch after upgrade.
- **REQ-INS-008 (M)** Installer validated on a clean machine (GitHub Windows runner
  + `--selftest`).

## 57. Clean-machine validation (CMT)

- **REQ-CMT-001 (M)** Validation on an environment without developer dependencies:
  installer, startup, activation, first-run setup, DB init, login, patient
  creation, visit, prescription, invoice, payment, backup, restore, printing/PDF,
  logout, auto-lock, uninstall, reinstall.

## 58. Stress testing (STR)

- **REQ-STR-001 (M)** Large patient counts; patients with many visits; long
  timelines; many prescriptions; many invoice items; many payments; large attachment
  collections; large search results; inventory history; backup/restore at realistic
  sizes; low disk space where safely possible; repeated navigation; repeated dialog
  open/close; long-running sessions; repeated lock/unlock.
- **REQ-STR-002 (M)** Watch for memory leaks, UI freezes, hangs, crashes,
  deadlocks, DB locks, corrupted records and rendering failures.

## 59. End-to-end acceptance test (E2E)

- **REQ-E2E-001 (M)** The full realistic clinic workflow (as enumerated in the
  master specification, § END-TO-END ACCEPTANCE TEST) must pass end to end,
  including restricted-user verification and final administrative actions.

## 60. UI acceptance audit (UAA)

- **REQ-UAA-001 (M)** Every screen inspected for alignment, spacing, typography,
  overflow, clipping, scrolling, responsive and High-DPI behaviour, button/icon/tab
  alignment, table/dialog/modal behaviour, focus states, keyboard navigation, and
  loading/empty/error/success/disabled/permission states.
- **REQ-UAA-002 (M)** No screen is complete merely because it renders.

## 61. No broken interaction (NBI)

- **REQ-NBI-001 (M)** Every interactive element works: buttons, tabs, sidebar items,
  dropdowns, comboboxes, date/time pickers, search, filters, pagination, tables,
  dialogs, drawers, file/folder selection, upload, download/export, print, preview,
  save, cancel, edit, delete, restore, lock, unlock, navigation, shortcuts.
- **REQ-NBI-002 (M)** If an element is visible it has a valid purpose and works.

## 62. File & folder handling (FFH)

- **REQ-FFH-001 (M)** Handles missing folder, permission denied, invalid path,
  nonexistent file, file already exists, insufficient disk space, locked file,
  corrupted file, invalid file type, interrupted operation — without crashing.

## 63. Backup validation (BKV)

- **REQ-BKV-001 (M)** A successfully created backup is not assumed valid: it is read
  back and verified.
- **REQ-BKV-002 (M)** A real backup → restore validation is performed before
  release.
- **REQ-BKV-003 (S)** Periodic restore test offered from Backup & Restore
  ("verify by test restore into a temporary workspace").

## 64. Data corruption protection (DCP)

- **REQ-DCP-001 (M)** Transactions, safe writes, integrity validation; no replacing
  the live DB with an unverified backup; no partially written files presented as
  valid; safe handling of termination during DB operations.

## 65. Dashboard & report accuracy (DRA)

- **REQ-DRA-001 (M)** Every displayed number originates from real business logic.
- **REQ-DRA-002 (M)** Dashboard totals verified against underlying transaction data
  in tests (independent recomputation assertion).

## 66. About screen (ABT)

- **REQ-ABT-001 (M)** Identifies the product as **Dentiva Pro** with version.
- **REQ-ABT-002 (M)** Creator/developer: **Shohan Khan**, email
  `helloiamshohan@gmail.com`, presented professionally.
- **REQ-ABT-003 (M)** No unnecessary internal technical information for ordinary
  users (technical details behind an expandable "System details" area).
- **REQ-ABT-004 (S)** Licence/activation status, third-party notices entry point.

## 67. Documentation (DCM)

- **REQ-DCM-001 (M)** Internal documentation for architecture, technology
  decisions, database schema, business rules, permissions, printing architecture,
  backup/restore behaviour, security decisions, activation architecture, testing
  strategy, build process, release process and known operational requirements.
- **REQ-DCM-002 (M)** Documentation reflects the actual implementation — no claims
  about features that do not exist.

## 68. Phase protocol (PHP)

- **REQ-PHP-001 (M)** Phase-by-phase execution; each phase completed, verified,
  tested, audited and reported before the next begins.
- **REQ-PHP-002 (M)** No skipped or silently merged phases; no phase marked complete
  with required work outstanding.
- **REQ-PHP-003 (M)** On "Continue", the repository state is inspected first;
  incomplete work is finished before new work.

## 69. Traceability (TRC)

- **REQ-TRC-001 (M)** Maintain a requirements traceability matrix: REQ ID →
  implementation location → entity/service → UI screen → test case → verification
  status → release status.
- **REQ-TRC-002 (M)** At every phase boundary the implementation is compared against
  the matrix; a full requirement-by-requirement audit precedes release.

## 70. Quality bar (QBR)

- **REQ-QBR-001 (M)** Works on a clean supported Windows environment; offline after
  activation; with realistic clinic data; multiple dentists; multiple users; large
  histories; Bangla and English; multiple Windows printers; all supported paper
  profiles; backup/restore; restricted permissions; after restart; after install;
  after uninstall/reinstall.
- **REQ-QBR-002 (M)** Does not corrupt data, expose restricted data, silently lose
  records, ship fake functionality, ship unfinished mandatory features, or ship
  known release-blocking bugs.

## 71. Release-blocking conditions (RBC)

- **REQ-RBC-001 (M)** Release is blocked by any of: incomplete mandatory feature;
  non-working required button; fake/placeholder screen; crashing critical workflow;
  patient-record corruption; clinical history overwrite; incorrect financial
  calculations; unauthorised financial access; unreliable backup; restore
  corrupting live data; broken prescription or invoice printing; corrupted Bengali;
  installer failure on a clean machine; uninstaller breaking install state; crashes
  in normal workflows; failing required GitHub Actions checks; failing required
  tests; unresolved critical/high release-blocking defect; broken DB relationships;
  dead buttons; mandatory TODOs; release-blocking UI clipping/overflow.

---

### Freeze statement
This baseline is the reference for all phases. Any change after Phase 1 must be
recorded here with a dated amendment note and reflected in
`docs/12-requirements-traceability.md`.

# Dentiva Pro — Database model (Phase 1 design; implemented in Phase 3)

Engine: **SQLite** (WAL), accessed through **SQLAlchemy 2.0**, schema owned by
**Alembic**. Final column-level DDL is produced by the Phase 3 models; this document
is the authoritative design contract and is kept in sync.

## 0. Global conventions

- Every table has `id INTEGER PRIMARY KEY` (surrogate) unless natural-keyed.
- Tenant scoping: every business table carries `business_id FK → business.id`
  (indexed). Even though v1 exposes one active business, the model supports
  several and the "delete business" destructive operation is well defined.
- Audit columns on mutable tables: `created_at_utc`, `updated_at_utc`,
  `created_by_user_id`, `updated_by_user_id`.
- Soft delete: `deleted_at_utc NULL` + `deleted_by_user_id` on patient, staff,
  user, inventory item, treatment catalog, dentist. Financial and clinical rows
  are **never** soft-deleted; they are voided/reversed with an audit entry.
- Money columns: `*_paisa INTEGER NOT NULL` (see ADR-0003).
- Timestamps: stored as **UTC ISO-8601 TEXT** plus (where a local business meaning
  matters) a local date column used for period filters and indexes.
- All FKs are declared with explicit `ON DELETE` behaviour: default `RESTRICT`
  for clinical/financial parents; `CASCADE` only for purely dependent children
  (e.g. invoice items → invoice, prescription items → prescription).
- `UNIQUE` constraints enforce business keys: `business.code`, `patient.code`
  (per business), `invoice.number` (per business), `payment.receipt_number`
  (per business), `user.username` (global), `permission.code`, `role.name`
  (per business).
- Foreign keys are **enforced** (`PRAGMA foreign_keys=ON` on every connection) and
  verified by `PRAGMA foreign_key_check` in System Health and before/after
  backup-restore.

## 1. Identity, tenancy & security

**business** — clinic/company: `name`, `legal_name`, `code` (unique), `logo_asset_id`,
`address_line1/2`, `city`, `district`, `postal_code`, `country`, `phone_primary`,
`phone_secondary`, `email`, `website`, `emergency_contact`, `registration_no`,
`tax_id`, `timezone`, `currency_code` ('BDT'), `currency_symbol` ('৳'),
`date_format`, `time_format`, `is_active`, `activated_at_utc`.

**dentist** — `business_id`, `staff_id NULL FK`, `display_name`, `first/last name`,
`registration_number` (unique per business), `specialty`, `bio`, `photo_asset_id`,
`signature_asset_id`, `phone`, `email`, `is_active`, `joined_on`, `sort_order`.
**dentist_designation** — `dentist_id`, `designation_id`, `is_primary`, `sort_order`.
**designation** — `business_id NULL` (global + clinic-specific), `name`, `abbr`,
`sort_order`, `is_active`.
**dentist_qualification** — `dentist_id`, `qualification_id`, `institution`, `year`,
`notes`. **qualification** — `name`, `abbr`, `sort_order`, `is_active`.
*Multiple designations and multiple qualifications are therefore first-class
(REQ-FRS-004).*

**staff** — `business_id`, `code`, `name`, `dob`, `age_cached`, `gender`,
`blood_group`, `nid_or_id_number`, `photo_asset_id`, `address`, `phone`, `email`,
`department/role_label`, `salary_paisa`, `joined_on`, `left_on`, `status`, `notes`.

**user** — `username` (unique), `password_hash` (PHC/Argon2id), `password_algo`,
`password_updated_at_utc`, `must_change_password`, `staff_id NULL`,
`dentist_id NULL`, `is_active`, `is_system_admin`, `last_login_at_utc`,
`failed_attempts`, `locked_until_utc`, `session_timeout_minutes NULL`.
**role** — `business_id NULL` (system templates + clinic roles), `name`,
`description`, `is_system`, `is_active`.
**permission** — `code` (unique, e.g. `invoice.create`), `group`, `label`,
`description`, `sensitive` (bool → triggers re-auth), `is_financial` (bool → used by
financial-access tests).
**role_permission** — `role_id`, `permission_id` (composite PK).
**user_role** — `user_id`, `role_id` (composite PK) — multiple roles per user;
effective permissions = union.
**session_record** — login/logout/lock audit trail: `user_id`, `started_at_utc`,
`ended_at_utc`, `end_reason`, `host`, `app_version`.

## 2. Patients

**patient** — `business_id`, `code` (unique per business), `name`, `guardian_name`,
`relation_of_guardian`, `dob`, `age_years_cached`, `age_updated_on`, `gender`,
`blood_group`, `marital_status`, `occupation`, `nid_or_passport`, `address_line1/2`,
`city`, `district`, `postal_code`, `country`, `phone_primary` (indexed),
`phone_secondary`, `emergency_contact_name`, `emergency_contact_phone`, `email`,
`preferred_language`, `referred_by`, `photo_asset_id`, `presenting_complaint`,
`past_medical_history`, `past_dental_history`, `allergies`, `current_medication`,
`habits` (smoking/betel/etc.), `notes`, `tags`, `first_visit_on`, `last_visit_on`,
`registered_at_utc`, `is_active`, `deleted_at_utc`.
Indexes: `(business_id, phone_primary)`, `(business_id, code)`,
`(business_id, registered_at_utc DESC)`, `(business_id, updated_at_utc DESC)`,
`(business_id, last_visit_on DESC)`, trigram-ish `(business_id, name_normalised)`.

**patient_attachment** — `patient_id`, `visit_id NULL`, `category`, `description`,
`original_filename`, `stored_relpath`, `mime_type`, `size_bytes`, `sha256`,
`uploaded_by_user_id`, `uploaded_at_utc`, `is_missing` (file absent on disk),
`deleted_at_utc`.
**patient_merge_log** — explicit, audited merges only: `kept_patient_id`,
`merged_patient_id`, `performed_by_user_id`, `reason`, `performed_at_utc`.
**patient_duplicate_flag** — detected candidates (never auto-merged):
`patient_id`, `candidate_patient_id`, `score`, `signals_json`, `status`.

## 3. Clinical

**visit** — `patient_id`, `business_id`, `number` (per patient sequence),
`visit_no_display`, `started_at_utc`, `ended_at_utc`, `local_date`,
`dentist_id`, `assisted_by_user_id`, `reason_for_visit`, `chief_complaint`,
`clinical_findings`, `examination_notes`, `diagnosis`, `treatment_plan`,
`notes`, `followup_advice`, `followup_on`, `status`
(`open|in_progress|completed|cancelled`), `queue_entry_id NULL`,
`appointment_id NULL`, `invoice_id NULL`, `next_appointment_id NULL`.
Indexes: `(patient_id, started_at_utc DESC)`, `(business_id, local_date)`,
`(dentist_id, local_date)`.

**visit_complaint** / **visit_examination** — `visit_id`, `catalog_item_id`,
`free_text`, `sort_order` (catalog-driven, REQ-CLN-001..004).
**clinical_catalog** — `business_id NULL`, `kind` (`complaint|examination|advice|
diagnosis|status`), `code`, `label`, `is_active`, `sort_order`.

**dental_chart** — `patient_id`, `visit_id NULL` (NULL = current/live chart),
`dentition` (`adult|primary|mixed`), `recorded_by_dentist_id`,
`recorded_by_user_id`, `recorded_at_utc`, `notes`, `is_active`.
**tooth_finding** — `chart_id`, `tooth_fdi` (11–48 / 51–85), `surfaces`
(serialised set: M/O/D/B/L/I), `status_id`, `note`, `visit_id`, `dentist_id`,
`recorded_at_utc`, `superseded_at_utc NULL`.
**tooth_status_catalog** — `code` (`normal|affected|caries|filled|treated|missing|
impacted|fractured|root_canal|crown|bridge|implant|supernumerary|other`),
`label`, `color_token`, `shape`, `is_active`, `sort_order`.
*History rule (REQ-MED-002): findings are only inserted; the "current" state is a
projection over the latest non-superseded finding per tooth, and "as of visit V" is
the projection over findings with `visit_id ≤ V`.*

**treatment_catalog** — `business_id`, `code`, `name`, `category_id`,
`default_price_paisa`, `duration_minutes`, `description`, `notes`, `is_active`,
`deleted_at_utc`. **treatment_category** — `name`, `sort_order`.

**treatment_record** — treatments *performed* (the clinical register):
`patient_id`, `visit_id`, `dentist_id`, `treatment_catalog_id NULL` (catalog item
can be retired later), `name_snapshot`, `category_snapshot`, `price_snapshot_paisa`
(NULL until billed), `tooth_fdi NULL`, `surfaces`, `quantity`, `notes`,
`status` (`planned|in_progress|completed|referred|cancelled`),
`performed_at_utc`, `invoice_item_id NULL`.
*Invoice lines snapshot name/price at billing time (REQ-TRT-004).*

**prescription** — `business_id`, `patient_id`, `visit_id NULL`, `dentist_id`,
`prescribed_at_utc`, `local_date`, `cc` (chief complaint), `oe` (on examination),
`re_or_advice`, ` diagnosis`, `notes`, `next_review_on`, `template_profile`,
`document_number`, `is_printed`, `printed_at_utc`, `voided_at_utc`.
**prescription_item** — `prescription_id`, `medicine_name`, `form`, `strength`,
`dose`, `frequency_code` (`1+1+1`, `0+0+1`, …), `morning/noon/night/other`
(quantities), `meal_relation` (`before|after|with|none`), `duration_days`,
`duration_label`, `quantity`, `instructions`, `is_prn`, `sort_order`,
`medicine_catalog_id NULL`.
**medicine_catalog** — `business_id NULL`, `name`, `form`, `strength`,
`is_active` (powers autocomplete; free text always allowed, REQ-PRX-004).

**referral** — `business_id`, `patient_id`, `visit_id NULL`, `referring_dentist_id`,
`destination_name`, `destination_specialty`, `destination_contact`, `reason`,
`notes`, `referred_on`, `status` (`open|accepted|completed|declined|cancelled`),
`followup_notes`, `followup_on`.

## 4. Scheduling

**appointment** — `business_id`, `patient_id`, `dentist_id NULL`,
`created_by_user_id`, `scheduled_start_utc`, `scheduled_end_utc`, `local_date`,
`duration_minutes`, `reason`, `notes`, `status`
(`scheduled|confirmed|arrived|completed|missed|cancelled|rescheduled`),
`visit_id NULL`, `queue_entry_id NULL`, `reminder_sent_at_utc`.
**appointment_status_history** — `appointment_id`, `from_status`, `to_status`,
`changed_by_user_id`, `changed_at_utc`, `reason`, `rescheduled_from_utc`.
*(Historical status preserved — REQ-APT-005.)*

**queue_entry** — `business_id`, `patient_id`, `appointment_id NULL`,
`visit_id NULL`, `dentist_id NULL`, `ticket_number` (per local date),
`status` (`waiting|called|in_consultation|completed|skipped|cancelled`),
`priority`, `created_at_utc`, `called_at_utc`, `started_at_utc`,
`completed_at_utc`, `called_by_user_id`, `notes`, `local_date`.
*One active queue entry per patient per day is enforced by a partial unique index.*

## 5. Billing & finance

**invoice** — `business_id`, `patient_id`, `visit_id NULL`, `number` (unique per
business), `issued_at_utc`, `local_date`, `issued_by_user_id`, `dentist_id NULL`,
`subtotal_paisa`, `discount_paisa`, `tax_paisa` (0 unless configured),
`total_paisa`, `paid_paisa`, `due_paisa`, `rounding_paisa`, `status`
(`draft|issued|partially_paid|paid|void|cancelled`), `notes`, `terms`,
`voided_at_utc`, `voided_by_user_id`, `void_reason`, `discount_reason`.
**invoice_item** — `invoice_id` (CASCADE), `treatment_catalog_id NULL`,
`treatment_record_id NULL`, `name_snapshot`, `description`, `tooth_fdi NULL`,
`quantity` (Decimal-free: integer + `unit_scale` for fractional units),
`unit_price_paisa`, `discount_paisa`, `line_total_paisa`, `sort_order`.
**payment** — `business_id`, `invoice_id`, `patient_id`, `received_by_user_id`,
`amount_paisa`, `paid_at_utc`, `local_date`, `method_id`, `reference_number`,
`notes`, `status` (`posted|void|refunded`), `idempotency_key` (unique per
invoice), `voided_at_utc`, `voided_by_user_id`, `void_reason`.
**payment_method** — `code` (`cash|bank|card|bkash|nagad|rocket|upay|other`),
`label`, `is_active`, `sort_order`, `requires_reference`.
**financial_summary** (recomputed cache, never hand-edited) — `patient_id`,
`total_billed_paisa`, `total_paid_paisa`, `outstanding_paisa`,
`last_invoice_at_utc`, `last_payment_at_utc`, `recomputed_at_utc`.
A nightly/on-demand **integrity job** recomputes from invoices+payments and reports
any drift (`System Health → Financial consistency`).

**expense** — `business_id`, `category_id`, `title`, `description`, `amount_paisa`,
`spent_on`, `paid_by_user_id`, `payment_method_id NULL`, `reference_number`,
`vendor_name`, `inventory_purchase_id NULL`, `attachment_id NULL`,
`recorded_at_utc`.
**expense_category** — `name`, `is_active`, `sort_order` (rent, electricity,
internet, accessories/supplies, staff salary, maintenance, other, custom).
**income** — non-payment income: `business_id`, `source`, `category`,
`amount_paisa`, `received_on`, `received_by_user_id`, `payment_method_id`,
`reference_number`, `notes`.

> **Source of truth rule (REQ-FIN-002/MON-001):** invoice totals and dues are
> computed by `domain.invoice_math` from items and payments; `financial_summary`
> and dashboard figures are derived through one shared query module
> (`repositories.finance`), never re-implemented per screen.

## 6. Inventory

**supplier** — `name`, `contact_person`, `phone`, `email`, `address`, `notes`,
`is_active`.
**inventory_item** — `business_id`, `code`, `name`, `category_id`, `supplier_id
NULL`, `unit` (`pcs|box|bottle|pack|vial|other`), `current_stock`
(integer, unit-consistent), `reorder_level`, `unit_cost_paisa`,
`default_sale_price_paisa NULL`, `location`, `notes`, `is_active`,
`deleted_at_utc`.
**inventory_batch** — `item_id`, `batch_no`, `supplier_id`, `purchase_id NULL`,
`quantity`, `remaining`, `unit_cost_paisa`, `manufactured_on`, `expiry_on`,
`received_on`, `notes`.
**inventory_purchase** — `business_id`, `supplier_id`, `purchased_on`,
`purchase_source`, `invoice_reference`, `total_cost_paisa`, `notes`,
`recorded_by_user_id`, `expense_id NULL`.
**inventory_purchase_line** — `purchase_id`, `item_id`, `batch_no`,
`quantity`, `unit_cost_paisa`, `expiry_on`, `line_total_paisa`.
**stock_movement** — `item_id`, `batch_id NULL`, `change` (signed integer),
`balance_after`, `reason` (`purchase|usage|adjustment|damage|expired|return|
restore`), `reference_type`, `reference_id`, `patient_id NULL`, `visit_id NULL`,
`note`, `performed_by_user_id`, `performed_at_utc`.
*Stock is only ever changed through `inventory_service`, which writes the movement
and the item balance in one transaction and audits it (REQ-STK-005/004).*

## 7. Operations: notifications, audit, backups, settings, printing

**notification** — `business_id`, `kind` (`appointment_upcoming|appointment_missed|
payment_outstanding|stock_low|stock_expiring|backup_success|backup_failure|
security|system`), `title`, `body`, `severity`, `entity_type`, `entity_id`,
`patient_id NULL`, `required_permission NULL`, `created_at_utc`, `expires_at_utc`.
**notification_read** — `notification_id`, `user_id`, `read_at_utc` (composite PK)
→ per-user read/unread with permission filtering.

**audit_log** — append-only (ADR-0009): `id`, `ts_utc`, `ts_local`, `business_id`,
`actor_user_id NULL`, `actor_username`, `actor_role_names`, `action`, `entity`,
`entity_id`, `patient_id NULL`, `visit_id NULL`, `summary`, `before_json`,
`after_json`, `severity`, `source`, `session_id`, `correlation_id`, `prev_hash`,
`row_hash`.

**backup_record** — `business_id`, `file_path`, `file_name`, `created_at_utc`,
`size_bytes`, `sha256`, `kind` (`manual|auto|pre_restore|pre_destructive`),
`status` (`in_progress|ok|failed`), `verified`, `verified_at_utc`,
`verification_error`, `app_version`, `schema_version`, `db_integrity`,
`triggered_by_user_id`, `notes`.

**settings** — key/value store, typed: `namespace`, `key`, `value_json`,
`value_type`, `updated_by_user_id`, `updated_at_utc`; unique `(namespace, key)`.
Sensitive entries are flagged and stored encrypted with the local key.
**number_sequence** — `business_id`, `scope` (`patient|invoice|payment|visit|
prescription|queue_ticket`), `prefix`, `next_value`, `padding`, `year_reset`.
**clinical_label / document_label** — configurable labels for document sections
(supports clinics that prefer Bangla section headings).

**printer_profile** — `business_id`, `name`, `paper` (`A4|A5|58mm|80mm|mini|custom`),
`width_mm`, `height_mm`, `margin_*_mm`, `orientation`, `base_font_pt`,
`template_variant` (`full|compact`), `printer_name NULL`, `is_default_for`
(`prescription|invoice|receipt|report`), `show_logo`, `show_signature`,
`footer_text`, `is_active`.
**print_job** — `document_type`, `document_id`, `profile_id`, `printer_name`,
`printed_at_utc`, `printed_by_user_id`, `pages`, `result` (`ok|cancelled|error`),
`error_message` (reprint history for the Print Center).

**asset** — managed binary assets (logo, photos, signatures): `relpath`, `mime`,
`size_bytes`, `sha256`, `kind`, `created_at_utc`.

## 8. Cross-cutting integrity rules

1. **No orphan records**: every FK is declared and enforced; deletion of a patient
   with clinical or financial history is refused and replaced by **archive**
   (`is_active=false`) — hard delete is a separate, authorised, safeguarded
   operation that first requires the history to be purged under its own
   permission and audit.
2. **Void, not destroy**: invoices and payments are voided/reversed; the original
   rows and their audit entries survive.
3. **Catalog snapshots**: invoice items, treatment records and prescriptions store
   name/price snapshots so later catalog edits cannot rewrite history.
4. **One transaction per business operation**; the unit of work commits once.
5. **Concurrency**: `version` integer (optimistic locking) on invoice, patient,
   inventory item; a stale save raises `ConflictError` and offers refresh.
6. **Uniqueness under concurrency**: unique constraints (not application-only
   checks) protect patient codes, invoice numbers, usernames, payment
   idempotency keys and queue tickets.
7. **Integrity checks**: `PRAGMA integrity_check`, `PRAGMA foreign_key_check`,
   audit-chain verification and the financial-consistency job are exposed in
   System Health and executed during backup verification and `--selftest`.

## 9. Indexing strategy (performance)
Composite indexes follow the real query shapes: patient list
`(business_id, registered_at_utc DESC)`; patient search `(business_id, phone_primary)`,
`(business_id, name_normalised)`; visits `(patient_id, started_at_utc DESC)`;
invoices `(business_id, issued_at_utc DESC)`, `(patient_id, issued_at_utc DESC)`,
`(status, due_paisa)`; payments `(business_id, paid_at_utc DESC)`,
`(invoice_id)`; appointments `(business_id, scheduled_start_utc)`,
`(patient_id)`; queue `(business_id, local_date, status)`; inventory
`(business_id, name)`, `(expiry_on)`, `(current_stock)`; audit
`(business_id, ts_utc DESC)`, `(entity, entity_id)`; notifications
`(business_id, created_at_utc DESC, kind)`.

## 10. Migrations
Alembic with `render_as_batch=True`; every revision is hand-reviewed, reversible
where feasible, and records its REQ link in the message. `alembic upgrade head`
runs inside the startup transaction; failure rolls back and shows a recovery
dialog that offers "restore from the last backup" (the pre-upgrade backup is taken
automatically when an upgrade is pending).

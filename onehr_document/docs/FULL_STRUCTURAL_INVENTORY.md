# onehr_document — Full Structural Inventory

## Persistent models

### `onehr.document.category`
Fields:
- code, name, description, company_id
- sensitivity, employee_visible, signature_required
- default_validity_days, default_reminder_days, default_grace_days, retention_days_after_expiry
- active
- valid_from, valid_to (effective-dated mixin)
- document_count, template_count

Key methods:
- create / write controlled by Document Manager
- effective overlap and non-negative governance constraints
- action_open_documents
- action_open_templates

### `onehr.document`
Fields:
- document_number, name, category_id, company_id
- employee_id, employee_number, responsible_user_id
- source_model_id, source_res_id, source_display_name
- template_id, keywords, state
- valid_from, valid_to
- version_ids, current_version_id
- version_count, signed_version_count, expiring_version_count
- esign_transaction_count

Key methods/actions:
- governed create/write + high-risk security audit
- source-reference validation with normal ORM `check_access("read")`
- action_activate / action_archive
- action_new_version
- action_generate_from_template
- action_open_versions / current version / employee / source / e-sign

### `onehr.document.version`
Fields:
- document_id, version, name
- company_id, employee_id, category_id, responsible_user_id
- template_version_id, state
- valid_from/valid_to plus effective_from/effective_to synchronization
- issue_date, expiry_date, grace_end_date, reminder_date
- retention_due_date, last_reminder_at, reminder_activity_id
- rendered_subject, rendered_content_html
- file_data (attachment-backed), file_name, mimetype, file_checksum
- issued_at/by, signed_at/by, expiry_reason
- esign_transaction_ids/count
- days_to_expiry, expiry_status

Key methods/actions:
- binary checksum/mimetype preparation
- unique version/date integrity
- controlled issue / request signature / mark signed / expire / archive
- successor creation without history rewrite
- QWeb Print PDF
- Store PDF Snapshot
- body-form Schedule Expiry Reminder
- open document/e-sign
- daily expiry/reminder cron
- uninstall-safe issued-history deletion protection

### `onehr.document.template`
Fields:
- code, name, description, category_id, company_id, active
- valid_from, valid_to
- version_ids/count, generated_document_count

Key methods/actions:
- manager-controlled create/write
- effective overlap and company/category integrity
- create version
- open versions/generated documents

### `onehr.document.template.version`
Fields:
- template_id, version, name, company_id, category_id
- state, valid_from, valid_to
- subject_template, body_html, filename_template
- variable_contract, content_checksum, generated_version_count

Key methods/actions:
- exact version/active overlap checks
- bounded variable contract validation
- activate / retire / create successor
- immutable after activation
- render_contract() with HTML-escaped values
- open template/generated versions

### `onehr.esign.transaction`
Fields:
- document_version_id, company_id, employee_id, category_id
- provider_key, correlation_id, provider_reference
- signer_name, signer_email, message
- state, requested_at/by, completed_at, status_note
- supersedes_id, superseded_by_id

Key methods/actions:
- controlled queue creation
- immutable provider-status update service
- dispatch_to_provider() soft-integration hook
- apply_provider_status()
- cancel
- open document version
- uninstall-safe deletion protection

## Transient models

### `wizard.document.generate`
- document/template/template-version
- company/employee/category/source
- document name and validity
- preview subject/html/filename
- Preview and Generate actions

### `wizard.document.publish.sign`
- document/version
- non-secret provider adapter key
- signer name/email/message
- dispatch flag
- Queue Signature Request action

## Security

Groups:
- Document User
- Document Officer
- Document Manager
- Document Compliance

Security design:
- global allowed-company rules
- employee self-read only for employee-visible internal records
- Officer/Manager operational scope excludes restricted records
- Compliance read scope includes restricted records
- Manager + Compliance becomes explicit dual gate for restricted mutation
- no custom-model ACL to `base.group_user`
- no persistent business-model unlink permission
- attachment-backed binary remains attached to the protected document-version model

## UI

Persistent models have dedicated list, form and search views.
Advanced patterns include statusbars, smart buttons, controlled header actions,
body-form reminder action, list/One2many row actions, chatter, ribbons,
decorations, pivot and graph analysis.

## Data/report

- `ir.sequence`: OneHR Document Number
- `ir.cron`: daily expiry/reminder governance
- QWeb PDF: Controlled HR Document

## Tests

Four post-install test modules cover Registry, document/version governance,
template generation, security/privacy, e-sign, expiry/reminder and attachment
binding.

# OneHR SOP — Full Structural Inventory

## Persistent business models — exactly three

### `onehr.sop`
Logical SOP master:
reference/title/company, owner, reviewer/approver matrix, review interval,
retention, acknowledgement reminder configuration, notification templates,
OneHR Document archive header, version navigation and current compliance KPIs.

### `onehr.sop.version`
Immutable governed content/version:
Draft → Review → Approved → Published → Obsolete, effectivity/review/retention,
purpose/scope/definitions, roles & responsibilities, work instructions, controls,
records/evidence, training, HSE/K3, references, unit/job/employee publication scope,
content fingerprint, OneHR Document archived snapshot, acknowledgement metrics and
audit CSV export.

### `onehr.sop.ack`
Per-employee publication evidence:
employee/user safe boundary, department/job snapshot, Pending/Acknowledged,
published/acknowledged timestamp, source and days-to-ack.

## Canonical models consumed — not duplicated
- `hr.employee`
- `hr.department`
- `hr.job`
- `res.company`
- `res.users`
- `mail.template`
- `mail.activity`
- `onehr.document.category`
- `onehr.document`
- `onehr.document.version`
- `onehr.mixin.audit`

## Deliberate non-invention
No extra persistent model for:
SOP templates, procedure lines, audience lines, notification queues, compliance
snapshots, branch mappings, portal records or API tokens.

Branch remains a downstream optional extension. Portal owns routes/session security.
Analytics owns dashboards/snapshots. Integrations API owns HTTP authentication.
Document owns immutable archived document payload/evidence.

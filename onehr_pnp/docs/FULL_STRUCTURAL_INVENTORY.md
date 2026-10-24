
# OneHR PnP — Full Structural Inventory

## Persistent business models — exactly three

### `onehr.policy`
One row is one controlled policy/procedure version. Stable `policy_code`,
`version_no`, `previous_policy_id` and `is_current` provide version/change history
without inventing a fourth persistent version model. It owns policy content,
effectivity/review/retention, targeted audience, approval-source integration,
publication, Document snapshot reference and portfolio compliance KPIs.

### `onehr.policy.ack`
Per-employee publication assignment and acknowledgement evidence:
policy/version snapshot, safe employee identity, department/job, due date,
Pending/Acknowledged/Not Required, acknowledgement timestamp/source,
reminder evidence and evidence navigation.

### `onehr.policy.evidence`
Compliance evidence using one approved model for all approved scopes:
Employee, Department/Unit and Policy-wide. Supports file/photo attachment,
controlled OneHR Document version, URL or compliance note. Workflow is
Draft→Submitted→Verified/Rejected with immutable submitted/verified content and
retained non-Draft history.

## Transient extension
`res.config.settings`:
default Policy Owner, review interval, acknowledgement reminder interval,
retention and default OneHR Document category.

## Canonical upstream models consumed — not duplicated
- `hr.employee`
- `hr.department`
- `hr.job`
- `res.company`
- `res.users`
- `ir.attachment`
- `mail.template`
- `onehr.mixin.audit`
- `onehr.mixin.approvable`
- `onehr.approval.request`
- `onehr.document.category`
- `onehr.document`
- `onehr.document.version`

## Deliberate non-invention
No persistent PnP model for category, version, audience line, review event,
notification queue, branch, Portal, API token or Analytics snapshot.

`onehr_sop` remains owner of operational SOP content/version/acknowledgement.
PnP stores only optional related SOP codes and resolves them at runtime when
OneHR SOP is installed and the caller has its own SOP access.


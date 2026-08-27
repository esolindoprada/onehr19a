# onehr_employment_contract — Full Structural Inventory

## `onehr.contract.template`
Versioned policy/applicability template. Fields cover code/name/version/company,
validity, state, default contract kind, engagement/grade/position/job applicability,
probation, notice, expiry reminder, approval SLA, document-template soft code and
notes. Actions: Activate, Retire, Create New Version, Open Contracts.

## `onehr.contract`
Legal/workflow wrapper linked to employee + canonical `hr.version` + exact template
version. Includes contract number/kind, predecessor-successor chain, governed state,
approval integration, live non-stored native facts, immutable approval snapshots,
expiry/reminder governance, termination request/approval/execution evidence,
termination clearance checklist, controlled line-manager display fields, soft document
generation/e-sign delegation and extension hooks for payroll/offboarding owners. Actions
include employee/directory navigation, native HR-version navigation, approval evidence,
renewal, expiry reminders, termination review/execution, documents/e-sign and clearance.

## Security
Groups: Contract Line Manager, Contract Officer, Contract Manager. Global company
rules; direct-report rule for line managers; controlled display-only employee/template/
position/grade/engagement labels for line managers; private HR navigation only for
Contract Officer/Manager; no `base.group_user` custom ACL and no ACL unlink rights.

## UI
Dedicated list/form/search for both persistent custom models; contract calendar,
pivot and graph; statusbars, smart buttons, header actions, body-form actions,
chatter and clearance-task One2many row actions.

## Data
Contract numbering sequence and daily expiry/reminder lifecycle cron.

## Tests
20 post-install runtime test methods across registry/template, workflow/integrity,
security/soft-integration/renewal/history domains.

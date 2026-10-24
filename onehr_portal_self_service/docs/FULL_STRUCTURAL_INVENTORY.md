
# OneHR Portal Self-Service — Full Structural Inventory

## Persistent business models — exactly three

1. `onehr.portal.request.type`
   - self-service service catalogue;
   - approval routing policy;
   - service kind and downstream contract selector;
   - SLA/reminder targets;
   - portal visibility and profile-field whitelist;
   - service-volume/open/overdue metrics.

2. `onehr.portal.request.stage`
   - enterprise display-stage catalogue mapped to the governed lifecycle;
   - shared/company-specific stage support;
   - portal visibility and Kanban fold behavior;
   - immutable mapping once transaction history exists.

3. `onehr.portal.request`
   - employee HR service transaction;
   - Draft → Submitted → Manager Review / HR Review → Approved → Processing → Done;
   - Rejected/Cancelled alternate terminal states;
   - manager/HR decision evidence;
   - SLA deadline/reminder/breach status;
   - attachments, chatter and activity evidence;
   - bounded service-specific payloads and downstream references.

## Native/shared extensions
- `res.users`: safe current-user employee/profile helpers and My HR action.
- `hr.employee`: self-service enablement and request smart button.

## Transient models
- `onehr.portal.request.decision.wizard`
- `onehr.portal.bulk.approval.wizard`

These are transient UI helpers, not persistent business masters.

## Intentionally not created
- duplicate employee/person master;
- duplicate leave policy/request master;
- duplicate Learning session/enrollment;
- duplicate Appraisal form;
- duplicate Document/category/version master;
- duplicate Payroll import/payslip master;
- duplicate Policy, SOP, Job Description or Career master;
- discipline evidence mirror;
- API token/webhook/authentication master;
- branch/legal-entity master.

## Technical structure
- `models/`: request catalogue, stage, transaction, native extensions and integration service layer.
- `controllers/`: authenticated employee/manager website routes only.
- `wizard/`: governed single/bulk decision helpers.
- `security/`: privilege groups, ACL and company/role record rules.
- `data/`: sequence, shared lifecycle stages, starter request types and SLA cron.
- `views/`: backend enterprise views, portal QWeb, employee extension and menus.
- `tests/`: lifecycle, security, ownership and integration-contract tests.
- `tools/`: static/source hard-gate acceptance.
- `docs/`: hard-gate evidence and runtime acceptance contract.


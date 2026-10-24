# Full Structural Inventory

## Persistent business models

### `onehr.offboarding`
Governed exit-orchestration case. Owns the offboarding workflow, organization/employee snapshot, checklist orchestration, exit-interview link, access-revocation disposition, final-benefit disposition, contract-termination disposition, readiness, completion/closure evidence and narrow downstream service payloads.

### `onehr.offboarding.checklist`
Generated cross-functional clearance task. Snapshots clearance catalogue fields and stores assignee, SLA, task state, asset-return disposition, notes, attachments and completion/waiver evidence.

### `onehr.clearance.item`
Reusable global/company clearance catalogue with category, owner role, mandatory flag, SLA, job/grade/exit-type applicability and operator instructions.

### `onehr.exit.interview`
One governed exit interview per case, including schedule, exit reason, experience scores, recommendation score, feedback, HR-confidential notes and submission/waiver evidence.

## Native extensions

### `hr.employee`
Derived-only `onehr_*` offboarding count/latest/exit indicators and smart-button navigation. It does not duplicate canonical employment facts.

### `res.users`
Controlled access-revocation evidence fields. Actual deactivation remains native `active=False` and additionally requires `base.group_system`.

## Technical/support inventory

- `models/action_helpers.py` — predictable action/notification helpers.
- `models/security_helpers.py` — explicit role checks.
- Four application groups.
- 11 ACL rows; no custom-model `base.group_user` CRUD.
- Four global company rules plus task-owner participation rules.
- Sequence `onehr.offboarding`.
- Daily clearance-SLA reminder cron.
- List/Form/Search for every persistent model.
- Kanban on cases/tasks, Calendar on tasks, Pivot/Graph on cases/interviews.
- Two QWeb reports.
- 40 post-install runtime test methods.

## Explicitly not created

- no `onehr.employee`
- no parallel employment contract or `hr.contract` owner
- no payroll calculation model
- no duplicate document/e-sign model
- no branch master
- no portal controller/session/auth layer
- no API token/controller/webhook layer
- no analytics snapshot/dashboard master

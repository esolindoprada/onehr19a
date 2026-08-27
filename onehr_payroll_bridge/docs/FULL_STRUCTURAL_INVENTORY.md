# onehr_payroll_bridge — Full Structural Inventory

## Models

### `models/config.py`
`onehr.payroll.bridge.config`

- company/external-system identity;
- CSV formatting;
- export/import field mapping;
- grade/position → external payroll structure mapping;
- attendance/overtime/time-off/assignment-costing inclusion policy;
- reconciliation policy/tolerance;
- monthly Draft export scheduling;
- non-secret adapter boundary.

### `models/export.py`
`onehr.payroll.export`

- payroll-period and employee scope;
- dynamic collection of available approved source variables;
- CSV generation;
- frozen source/config JSON evidence;
- SHA-256 source fingerprint;
- Draft → Posted to Payroll → Reconciled workflow;
- vendor CSV upload/import orchestration;
- reconciliation KPI and time-to-close;
- department costing payload;
- stable downstream adapter payload.

### `models/import_result.py`
`onehr.payroll.import`

- employee/vendor result evidence;
- employee/org/grade/position snapshots;
- gross/deduction/net/employer cost;
- validation and optional net-equation tolerance;
- immutable correction revision chain;
- portal-safe payload service;
- API-adapter ingestion service under normal payroll authority.

### Helper modules

- `models/action_helpers.py`: readable Odoo action builders.
- `models/authority_helpers.py`: explicit Officer/Manager authority checks.

No helper file owns a persistent business model.

## Security

- Payroll Officer: prepare exports/imports and validate results.
- Payroll Manager: configuration, posting, reconciliation, correction and governed draft cleanup.
- Payroll roles do **not** imply OneHR sensitive/restricted Core HR reader roles.
- company record rules on all three models.
- no `base.group_user` custom-model CRUD.
- no business `sudo()` bypass.

## Data

- payroll export/import sequences;
- daily scheduler prepares Draft batches only;
- scheduler never auto-posts or auto-reconciles payroll.

## UI / analytics

- all three models have explicit List + Form + Search.
- Export: Statusbar, header actions, smart buttons, body actions, One2many row actions,
  Calendar, Pivot, Graph and QWeb reconciliation report.
- Import: Statusbar, smart/body/row actions, revision history, Pivot and Graph.
- Configuration: mapping-oriented professional form, smart/body/O2M actions.

## Historical controls

- posted/reconciled source facts are immutable;
- validated/reconciled import rows are immutable;
- corrections create a new revision and supersede prior evidence;
- used configuration is archived instead of deleted;
- `@api.ondelete(at_uninstall=False)` preserves production history without blocking uninstall.

## Generic scaffold removed

The tutorial controller, placeholder model, demo records, `views/views.xml`,
`views/templates.xml`, version `0.1`, `base`-only manifest and broad
`base.group_user` CRUD are not part of this build.

- Native Odoo `hr.work.entry` is consumed dynamically when installed; Draft/Validated work entries are exported without generation or mutation.

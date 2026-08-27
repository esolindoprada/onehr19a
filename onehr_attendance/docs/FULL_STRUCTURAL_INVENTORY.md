# onehr_attendance — Full Structural Inventory

## Python structure

- `models/action_helpers.py` — predictable form/list actions and notifications.
- `models/shift.py` — Shift, Rotation Pattern and Employee Shift Schedule.
- `models/attendance.py` — Odoo `hr.attendance` enterprise extension and ingestion/reconciliation service.
- `models/exception.py` — immutable attendance-exception evidence.
- `models/import_reconciliation.py` — fingerprint/device import batch and governed reconciliation.
- `models/native_overtime.py` — Odoo 19 native overtime line/rule/ruleset metadata extensions.

## Persistent custom models

1. `onehr.shift`
2. `onehr.shift.pattern`
3. `onehr.shift.assignment`
4. `onehr.attendance.exception`
5. `onehr.attendance.reconciliation`
6. `onehr.attendance.import.batch`

## Odoo-native extensions

1. `hr.attendance`
2. `hr.attendance.overtime.line`
3. `hr.attendance.overtime.rule`
4. `hr.attendance.overtime.ruleset`

## Security

- Attendance Officer and Attendance Manager Odoo 19 privileges/groups.
- 15 ACL rows: 12 custom model ACLs + 3 read-only support ACLs for employee/position/work calendar.
- 6 company record rules on custom OneHR Attendance models.
- No `base.group_user` custom-model CRUD.
- Attendance Officer intentionally does not imply Core HR Officer or `hr.group_hr_user` merely to render employee selectors.

## Data / automation

- Import Batch sequence `onehr.attendance.import.batch`.
- Reconciliation sequence `onehr.attendance.reconciliation`.
- Daily schedule-state refresh cron.
- Daily prior-day missing-punch detection cron.

## UI / reports

- Shift, Pattern, Schedule: explicit list/form/search.
- Attendance: dedicated list/form/search/calendar/pivot/graph over native `hr.attendance`.
- Exception: list/form/search/pivot/graph.
- Import Batch: list/form/search.
- Reconciliation: list/form/search.
- Native overtime line: list/form/search/pivot/graph.
- Native overtime rule: list/form/search.
- Native overtime ruleset: list/form/search.
- QWeb Attendance Record PDF.
- QWeb Attendance Reconciliation Control PDF.

## Runtime tests

29 post-install runtime test methods across shift/scheduling, attendance workflow, import/reconciliation, security and native overtime contracts.

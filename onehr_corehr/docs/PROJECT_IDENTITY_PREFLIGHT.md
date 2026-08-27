# onehr_corehr — Project Identity Preflight

PROJECT: OneHR NEW

ADDON: onehr_corehr

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1.
- Frozen OneHR 25-addon topology/dependency table.
- Latest user-provided OneHR workspace dump.
- Accepted onehr_base and onehr_security contracts.
- Official Odoo 19 native HR model behavior.

PRESERVATION RULE:
- Preserve Core HR functionality, not obsolete scaffold ownership.
- Native `hr.employee` + `hr.version` are the employee master.
- `hr.employee.public` exposes only explicitly safe OneHR directory fields.
- Personal document storage/expiry/reminders belong to `onehr_document`.
- Prior external employment history belongs here; internal placement belongs to `onehr_assignment`.
- Occupational health is isolated and explicitly authorized.

ALLOWED CHANGE:
- Full scaffold replacement.
- Odoo 19 native-first reconstruction.
- Registry-approved models/fields/workflows only.
- Advanced enterprise UI and safe report.
- Least-privilege security and audit evidence.
- Tests, source acceptance and Windows runtime acceptance tooling.

FORBIDDEN CHANGE:
- No `onehr.employee`.
- No parallel department/job/work-location.
- No `onehr.employee.document`.
- No custom import wizard model.
- No branch ownership.
- No broad `base.group_user` CRUD.
- No medical access inherited merely from HR Manager or Security Admin.
- No dependency other than `onehr_base`, `onehr_security`, `hr`.

CURRENT VERIFIED STATUS:
- Uploaded addon is a generic scaffold with version 0.1 and base-only dependency.
- Direct Full Build source is reconstructed in this package.
- Windows/Odoo runtime is not executed in the build environment.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_SOURCE_BUILD

# onehr_assignment — Project Identity Preflight

PROJECT: OneHR NEW

ADDON: onehr_assignment

TARGET: Odoo 19 Community Edition

DELIVERY METHOD: Direct Full Addon Build

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1.
- Frozen 25-addon dependency/ownership topology.
- Latest accepted OneHR base, Core HR, Security and Workflow Approval source contracts.
- Latest user-provided OneHR workspace dump.
- Odoo 19 native HR versioning behavior.
- OneHR 25 Addons Specification and Oracle HRMS benchmark for Assignment/Position/Budget/Costing behavior.

PRESERVATION RULE:
- Assignment owns internal placement/movement history.
- Odoo `hr.employee` remains the worker master; Odoo `hr.version` remains the native temporal employment store.
- `onehr.position` remains the enterprise seat/headcount/FTE authorization.
- Assignment owns occupancy consumption, not a duplicate position master.
- Cost allocation stays payroll/accounting-neutral.
- Workforce planning/position budget remains in this addon.

ALLOWED CHANGE:
- Replace generic tutorial scaffold completely.
- Implement exactly the seven Registry-owned persistent models.
- Add safe native extensions, professional views, workflow integration, tests and evidence.

FORBIDDEN CHANGE:
- No duplicate employee/job/department/work-location models.
- No branch model ownership.
- No payroll/accounting hard dependency.
- No Employment Contract reverse/hard dependency.
- No broad internal-user CRUD.
- No business sudo bypass.
- No unregistered movement wizard.

CURRENT VERIFIED STATUS:
- Uploaded `onehr_assignment` baseline was version 0.1/base-only tutorial scaffold.
- Direct Full source has been reconstructed in this package.
- Windows/Odoo runtime is not executed in this build environment.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_SOURCE_BUILD

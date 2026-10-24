
# OneHR Portal Self-Service — Direct Full Addon Implementation Report

BUILD: Direct Full Addon Build
TARGET: Odoo 19 Community Edition
VERSION: 19.0.1.0.2
SOURCE WRITE SCOPE: `onehr_portal_self_service` only
CODEX ROLE: bounded implementation worker only

## Delivered enterprise coverage
- exact three persistent Portal business models from the supplied product contract;
- `res.users` / `hr.employee` extensions without duplicate worker ownership;
- authenticated My HR and My Team portal journeys;
- governed employee Draft/Submit/Cancel and manager/HR decision lifecycle;
- approval timestamps, decision actor and decision note evidence;
- configurable request catalogue, company/shared stages and SLA targets;
- hourly SLA reminder monitor and searchable overdue status;
- attachments, chatter and activities;
- Profile Change with scalar-field whitelist and HR-authority write to canonical employee;
- bounded Time Off, Learning and Document downstream services with no ACL bypass;
- read-only soft Appraisal, Payroll, JD, PnP, SOP and Career dashboard contracts;
- explicit Discipline confidentiality boundary;
- portal chatter privacy boundary: internal mail subtypes are filtered before QWeb rendering;
- non-HR final approvals never inherit Portal HR/downstream execution authority; auto-execution is deferred as Pending for an authorized HR operator;
- portal-external employee/manager actions do not depend on internal `mail.activity` creation rights;
- portal uploads use the governed `mail.thread.message_post()` attachment path with 10-file, 10 MB/file and 25 MB/request limits instead of broad direct `ir.attachment` creation;
- enterprise backend List/Form/Search for every persistent model;
- Request Kanban, Calendar, Pivot and Graph;
- statusbar, Action Buttons, Smart Buttons, Body Buttons, badges/ribbons and One2many row buttons;
- decision and bulk-action transient wizards;
- least-privilege Portal Employee/Manager/HR/Admin security;
- Odoo 19 `res.groups.privilege`, `<list>`, direct modifiers and `models.Constraint` patterns;
- HARD GATE 11 identifier and relation-name controls;
- 34 post-install test methods;
- source acceptance and runtime acceptance evidence contracts.

REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY: NO

## Runtime Repair Attempt 2

Windows activation on Odoo `19.0.20251217` failed before registry completion because
`security/onehr_portal_security.xml` referenced the nonexistent external ID
`portal.group_portal`.

Release `19.0.1.0.1` replaces only that reference with the Odoo 19 canonical
`base.group_portal`. No model, feature, dependency, ACL, record rule, lifecycle,
integration contract or ownership boundary changed.

Regression prevention now checks the canonical XML ID in source acceptance and adds a
post-install test for the Portal Employee user type.

ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE  
ATTEMPT: 2/2  
WINDOWS_RUNTIME_RETEST: PENDING  
ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY: NO


## New Bounded Runtime Repair Task — Attempt 1/2

After the prior repair task reached its configured limit, the reviewer explicitly approved
`ONEHR-PORTAL-RUNTIME-REPAIR-20260829-B`. The next Windows activation progressed past the
Portal group XML-ID defect and exposed a distinct Odoo 19 loader defect in
`views/wizard_views.xml`:

`ValueError: Invalid field 'groups_id' in 'ir.actions.act_window'`

Release `19.0.1.0.2` replaces that one invalid field name with `group_ids`. The action's
Portal Manager/Portal HR restriction is preserved; it is not removed or broadened. Source
acceptance now rejects this exact field-name regression and test 34 verifies the runtime
`group_ids` membership contract.

ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE  
NEW_BOUNDED_TASK_ATTEMPT: 1/2  
WINDOWS_RUNTIME_RETEST: PENDING  
ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY: NO

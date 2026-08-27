# OneHR Appraisal — Direct Full Addon Implementation Report

BUILD: Direct Full Addon Build  
TARGET: Odoo 19 Community Edition  
VERSION: 19.0.1.0.1  
SOURCE WRITE SCOPE: `onehr_appraisal` only  
CODEX ROLE: bounded implementation worker only

## Authoritative product alignment

The build implements exactly the three Appraisal product models:

- `onehr.appraisal.cycle`
- `onehr.appraisal.form`
- `onehr.appraisal.score`

Hard dependencies remain exactly:

- `onehr_corehr`
- `onehr_security`

No Appraisal-specific employee, competency, talent, Learning, Analytics, API-authentication,
or workflow-approval master is invented.

## Enterprise functional coverage

- annual / biannual / quarterly / custom appraisal cycles;
- weighted Objective/OKR/KPI target templates and rating scale;
- idempotent employee appraisal-form generation;
- self / manager / peer multi-rater evidence;
- configurable rater activation: a 0% rater weight becomes explicitly Not Required;
- comments, attachments, chatter and activities;
- Draft → In Review → Consolidation → Closed workflow;
- submitted-rating evidence lock and controlled lifecycle transitions;
- final rating distribution and optional 9-box;
- employee acknowledgement;
- Individual Development Plan and governed soft hand-off to OneHR Learning;
- Analytics, Career/Succession, Discipline, Portal and Integrations API model-service contracts;
- KPI target CSV import and appraisal-result CSV export;
- review deadline reminder cron;
- configurable appraisal evidence retention horizon;
- QWeb PDF appraisal report;
- multi-company isolation and privacy-safe participant/manager employee display;
- grade dimension for result distribution.

## Professional UI

- Header Action Buttons and Statusbar Widgets.
- Smart Buttons for objectives, peer feedback, development and printing.
- Body action buttons for detailed score workspaces/import/export.
- One2many row actions for multi-rater feedback and development lifecycle.
- Dedicated List/Form/Search for every persistent model.
- Cycle Kanban/Calendar.
- Appraisal and score Pivot/Graph analysis.
- Badges, ribbons, chatter/activity and safe employee display snapshots.

## Security

- no custom `base.group_user` CRUD;
- no business `sudo()`;
- no public Appraisal controller;
- global company rules;
- Participant = own appraisal + assigned peer score rows only;
- Manager = assigned team;
- HR = company appraisal operations;
- HR Manager = governed administrative authority;
- peer reviewer does not gain full-form visibility for another employee;
- raw private `hr.employee` references are HR-restricted where practical;
- lifecycle/evidence deletion guards preserve started/submitted history.

## Runtime status

Source acceptance is a prerequisite only. It does not prove Windows/Odoo runtime completeness.

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`

`ONEHR_APPRAISAL_MOVE_FORWARD_READY: NO`

## Runtime Repair Attempt 2

The first Windows activation exposed an Odoo 19 decorator compatibility defect:
`@api.depends("template_score_ids.id", ...)` is rejected during model import.

Repair 19.0.1.0.1 replaces that dependency with the supported relational
dependencies `template_score_ids` and `template_score_ids.parent_score_id`.
No enterprise capability or architecture ownership changed.

`ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE`
`ATTEMPT: 2/2`

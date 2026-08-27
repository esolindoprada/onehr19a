# OneHR Discipline — Direct Full Implementation Report

BUILD: Direct Full Addon Build  
TARGET: Odoo 19 Community Edition  
VERSION: 19.0.1.0.1  
SOURCE WRITE SCOPE: `onehr_discipline` only  
CODEX ROLE: bounded implementation worker only

Delivered:
- exactly two authoritative persistent Discipline models;
- exact hard dependency topology;
- legacy feature-intent preservation without unapproved model proliferation;
- confidential incident/case pipeline;
- investigation and hearing evidence;
- violation classification/weight;
- case SLA and reminder activities;
- formal sanction decision with Workflow Approval;
- SP1/SP2/SP3, warnings, suspension, probation, last chance, payroll request,
  termination recommendation and no-action decisions;
- appeal process embedded in Case;
- employee service/receipt evidence;
- soft Appraisal/PnP/Document/Payroll/Contract/Analytics/API contracts;
- repeat-offense and resolution-time analytics;
- six QWeb reports/letters;
- enterprise List/Form/Search for both models;
- Kanban, Hearing Calendar, Pivot/Graph;
- statusbars, smart buttons, body actions and One2many row actions;
- strict Investigator/HRBP/Manager/Legal-IR security;
- HARD GATE 11 identifier scanner;
- 50 post-install test methods.

REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_DISCIPLINE_MOVE_FORWARD_READY: NO

## Runtime Repair Attempt 1 — 2026-08-24

First Windows activation reached Search View validation and failed because
`repeat_offense` was computed/non-stored but not searchable while the Search View
used `[('repeat_offense', '=', True)]`.

Repair `19.0.1.0.1` adds the explicit ORM search method while preserving the
dynamic, cross-record Repeat Offense semantics. No functional scope, security,
ownership or dependency topology changed.

`ROOT_CAUSE_CLASSIFICATION: ADDON_SOURCE_FAILURE`  
`ATTEMPT: 1/2`

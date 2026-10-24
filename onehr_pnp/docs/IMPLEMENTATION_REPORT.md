
# OneHR PnP — Direct Full Implementation Report

BUILD: Direct Full Addon Build  
TARGET: Odoo 19 Community Edition  
VERSION: 19.0.1.0.1  
SOURCE WRITE SCOPE: `onehr_pnp` only  
CODEX ROLE: bounded implementation worker only

Delivered:
- exactly three persistent PnP models + approved Settings transient extension;
- exact hard dependency topology;
- controlled version/change history without inventing a fourth version model;
- OneHR Workflow Approval routing/finalization contract;
- targeted company/department/job/employee publication + branch extension key;
- generated employee acknowledgement assignments and Read & Acknowledge evidence;
- employee, Department/Unit and policy-wide compliance evidence;
- file/photo attachment, controlled Document, URL and note evidence types;
- periodic review, retention and acknowledgement reminder governance;
- publication/reminder email templates;
- OneHR Document immutable published snapshot and successor header reuse;
- Policy, compliance, review/expiry and evidence coverage reports;
- Portal/API/Analytics model-service boundaries;
- soft OneHR SOP references without ownership duplication;
- List/Form/Search all persistent models;
- Kanban/Calendar/Pivot/Graph;
- statusbars, smart buttons, body actions and One2many row actions;
- least-privilege company/assignment/evidence security;
- HARD GATE 11 source scanner;
- 49 post-install test methods.

REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_PNP_MOVE_FORWARD_READY: NO


## Odoo 19 User Access Rights compatibility repair — 2026-09-10

ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`

The native Odoo 19 Users form dynamically renders `ir.module.category.name` values
inside generated XML for the Access Rights widget. The prior category display name
`OneHR Policies & Procedures` contains an XML-sensitive ampersand after
entity decoding, which can make the browser's generated XML malformed.

Bounded repair:
- category XML ID is unchanged: `onehr_pnp.module_category_onehr_pnp`;
- category display name is now `OneHR Policies and Procedures`;
- privilege XML ID and privilege display name are preserved;
- models, fields, methods, workflow, dependencies, ACLs, record rules, effective dating,
  integrations and enterprise UI remain unchanged;
- a cross-suite source gate and post-install dynamic-XML regression test are added.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`


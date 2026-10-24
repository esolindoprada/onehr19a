
# OneHR Career & Succession — Direct Full Implementation Report

BUILD: Direct Full Addon Build  
TARGET: Odoo 19 Community Edition  
VERSION: 19.0.1.0.1  
SOURCE WRITE SCOPE: `onehr_career_succession` only  
CODEX ROLE: bounded implementation worker only

## Product alignment
The build follows the approved Career/Succession baseline exactly:
four persistent models and hard dependencies only `onehr_base`, `onehr_corehr`.

## Enterprise coverage
- competency dictionary with level/behaviour anchors;
- position competency requirement matrix;
- native Odoo competency CSV import;
- talent pool and high-potential classification;
- performance/potential/competency/learning readiness components;
- 9-box and readiness classification;
- career aspiration, mobility and development evidence;
- critical-position succession plans with multiple successor candidates;
- primary successor, target coverage, bench strength, readiness and risk index;
- Draft → Proposed → Approved → Active governance;
- source-evidence refresh from Appraisal/Learning when installed and authorized;
- Analytics/Portal/API model service contracts;
- review reminder cron;
- gap-analysis and succession-plan PDFs;
- professional List/Form/Search/Kanban/Pivot/Graph UI;
- company isolation, audit/chatter and evidence-preservation controls.

## Deliberate architecture boundaries
No fifth business model was invented for competency assessment, career paths, candidate
lines, 9-box cells, scoring rules, import wizard or API authentication.

## Runtime status
`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`  
`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`  
`ONEHR_CAREER_SUCCESSION_MOVE_FORWARD_READY: NO`


## Odoo 19 User Access Rights compatibility repair — 2026-09-10

ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`

The native Odoo 19 Users form dynamically renders `ir.module.category.name` values
inside generated XML for the Access Rights widget. The prior category display name
`OneHR Career & Succession` contains an XML-sensitive ampersand after
entity decoding, which can make the browser's generated XML malformed.

Bounded repair:
- category XML ID is unchanged: `onehr_career_succession.module_category_onehr_career_succession`;
- category display name is now `OneHR Career and Succession`;
- privilege XML ID and privilege display name are preserved;
- models, fields, methods, workflow, dependencies, ACLs, record rules, effective dating,
  integrations and enterprise UI remain unchanged;
- a cross-suite source gate and post-install dynamic-XML regression test are added.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`


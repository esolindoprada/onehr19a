
# onehr_pnp — Odoo 19 User Access Rights Compatibility Repair

TASK_ID: `ONEHR-USER-ACCESS-RIGHTS-COMPAT-20260910`  
TARGET_ADDON: `onehr_pnp`  
WRITE_SCOPE: `onehr_pnp` only  
ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`  
BASELINE_VERSION: `19.0.1.0.0`  
REPAIR_VERSION: `19.0.1.0.1`

## Proven runtime failure class

Odoo 19's native Users Access Rights widget builds a category-group XML fragment from
`ir.module.category.name`. When a stored category name contains XML-sensitive text such
as a decoded `&`, the generated browser XML can fail parsing even though the original
server-side XML data file was valid (`&amp;`).

## Bounded correction

Only the owned module-category display value changes:

- XML ID: `onehr_pnp.module_category_onehr_pnp` — preserved
- Before: `OneHR Policies & Procedures`
- After: `OneHR Policies and Procedures`
- Privilege XML ID: `onehr_pnp.privilege_onehr_pnp` — preserved
- Privilege display name: `OneHR Policies & Procedures` — preserved

No model, field, method, workflow state, sequence, dependency, ACL, record rule, company
boundary, effective-dating rule, ownership contract, integration, report or enterprise UI
feature is changed by this repair.

## Deterministic closure gate

The repair adds two layers:

1. `tools/source_acceptance.py` scans privilege-bearing OneHR module categories from
   sibling OneHR addon source and rejects decoded XML-sensitive category labels before runtime.
2. Post-install regression reconstructs the same dynamic XML shape and parses every installed
   OneHR privilege category. It also verifies this addon's category and privilege XML IDs remain
   bound as expected.

The authoritative 2026-09-10 composite source contained 24 privilege-bearing OneHR
categories. Exactly two were unsafe before the bounded overlay: Career/Succession and PnP.
The paired repair normalizes both; this task does not rename unrelated labels.

`STATIC_RESULT: PASS — 121 checks / 0 FAIL; 49 runtime tests packaged`  
`WINDOWS_RUNTIME_RESULT: NOT_RUN`  
`MOVE_FORWARD_READY: NO`


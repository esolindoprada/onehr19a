
# OneHR Workflow Approval — Runtime Compatibility Repair 2026-08-14

TASK_ID: ONEHR_WORKFLOW_APPROVAL_RUNTIME_COMPATIBILITY_REPAIR_V1_20260814

PROJECT: OneHR NEW  
ADDON: `onehr_workflow_approval`  
TARGET_RUNTIME: Odoo 19.0.20251217  
ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE  
CODEX_EXECUTED: NO  
ARCHITECTURE_CHANGE: NO  
REGISTRY_CHANGE: NO  
DEPENDENCY_CHANGE: NO  
SECURITY_WEAKENING: NO  
TEST_METHOD_COUNT_CHANGE: NO

## Runtime evidence

Install reached Odoo registry/model field setup and failed before module data loading:

`ValueError: Field model_id of model onehr.approval.rule is defined as ondelete='restrict' while having ir.model as comodel, the 'restrict' mode is not supported for this type of field as comodel.`

The proven source location was:

`models/approval_rule.py` → `onehr.approval.rule.model_id`

## Odoo 19 mechanism

Odoo 19 `Many2one.setup_nonrelated()` rejects `ondelete="restrict"` when the
comodel is one of Odoo's framework `IR_MODELS`. A required Many2one also cannot
use `ondelete="set null"`. Therefore this required `ir.model` relation must use
`ondelete="cascade"` to remain compatible without making the field optional.

## Approved correction

Before:

`model_id = fields.Many2one("ir.model", required=True, ondelete="restrict", ...)`

After:

`model_id = fields.Many2one("ir.model", required=True, ondelete="cascade", ...)`

No model, field, workflow, rule criterion, security group, ACL, record rule,
business action, view, dependency, effective-dating contract or historical
decision behavior was removed or simplified.

## Prevention

`tools/source_acceptance.py` now checks all Odoo 19 framework metadata comodels:

- `ir.model`
- `ir.model.data`
- `ir.model.fields`
- `ir.model.fields.selection`
- `ir.model.relation`
- `ir.model.constraint`
- `ir.module.module`

and fails source acceptance if a required metadata Many2one would default to
`restrict`, explicitly uses `restrict`, or incorrectly uses `set null`.

The existing runtime test inventory remains exactly 20 methods. One existing test
also asserts that `onehr.approval.rule.model_id.ondelete == "cascade"`.

## Gate status after source repair

SOURCE_STATIC_ACCEPTANCE: PASS required before release  
FRESH_INSTALL: RETRY_REQUIRED  
RUNTIME_TESTS: NOT_RUN_AFTER_REPAIR  
FIRST_UPGRADE: NOT_RUN  
REPEAT_UPGRADE: NOT_RUN  
POST_UPGRADE_SMOKE: NOT_RUN  
UNINSTALL_REINSTALL: NOT_RUN  
MOVE_FORWARD_READY: NO

No next OneHR addon may be started based only on this source repair.

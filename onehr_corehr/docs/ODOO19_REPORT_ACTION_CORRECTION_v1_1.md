# onehr_corehr — Odoo 19 Report Action Compatibility Correction v1.1

ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE
PROVEN_SOURCE_DEFECT: YES
TARGET_ADDON: onehr_corehr
CODEX_USED: NO
ARCHITECTURE_CHANGE: NO
MODEL_OWNERSHIP_CHANGE: NO
DEPENDENCY_CHANGE: NO
SECURITY_WEAKENING: NO

## Failure

Odoo 19.0.20251217 rejected the Employee Profile report action because the
XML used `groups_id`, which is not a field on this runtime's `ir.actions.report`.

## Bounded correction

Only the report-action group field is corrected:

- BEFORE: `groups_id`
- AFTER: `group_ids`

The existing `onehr_corehr.group_onehr_corehr_officer` report restriction is
preserved.

The source acceptance gate is also hardened so the invalid spelling cannot pass
static/source review again.

WINDOWS_RUNTIME_RECHECK: PENDING
ONEHR_COREHR_MOVE_FORWARD_READY: NO

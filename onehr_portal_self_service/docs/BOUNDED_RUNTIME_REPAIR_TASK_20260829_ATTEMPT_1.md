# OneHR Portal Self-Service — New Bounded Runtime Repair Task, Attempt 1

TASK_ID: `ONEHR-PORTAL-RUNTIME-REPAIR-20260829-B`  
USER_APPROVAL: `APPROVE NEW BOUNDED REPAIR TASK`  
ATTEMPT: 1 of 2  
DATE: 2026-08-29  
TARGET_PLATFORM: Odoo 19 Community Edition (`19.0.20251217`)  
SOURCE_WRITE_SCOPE: `onehr_portal_self_service` only  
ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`

## Why this is a new task

The earlier Direct Full Build repair task consumed its two-attempt allowance and correctly
stopped after release `19.0.1.0.1`. The reviewer then explicitly authorized a new bounded
repair task. This document starts that new task at Attempt 1/2; it does not rewrite the
history of the earlier task or create an unlimited retry loop.

## Runtime evidence

Activation of `onehr_portal_self_service` failed while Odoo loaded:

`views/wizard_views.xml`

The failing record is the bound window action:

`action_onehr_portal_bulk_approval_wizard`

Odoo raised:

`ValueError: Invalid field 'groups_id' in 'ir.actions.act_window'`

The latest supplied workspace contains exactly one XML `<field name="groups_id">`
occurrence, and it is this action. Other current OneHR action definitions use `group_ids`.

## Bounded architecture-preserving correction

Only the proven ORM field-name mismatch is corrected:

- before: `ir.actions.act_window.groups_id`
- after: `ir.actions.act_window.group_ids`

The two linked OneHR groups remain unchanged:

- `group_onehr_portal_manager`
- `group_onehr_portal_hr`

The field is not deleted, so the bound action remains hidden from ordinary Portal Employees.
Model ACL, record rules and wizard business-method authority remain the security boundary.

Manifest release marker is bumped from `19.0.1.0.1` to `19.0.1.0.2`.

## Regression prevention

`tools/source_acceptance.py` now:

- rejects `groups_id` on every target-local `ir.actions.act_window` record;
- requires the Bulk Request Decision action to use `group_ids`;
- expects release `19.0.1.0.2`;
- inventories 34 post-install tests;
- ignores blank CSV lines when counting ACL rows so source evidence reports the real 14 ACL records.

`tests/test_security.py` adds a post-install contract test proving the bound action includes
Portal Manager and Portal HR in `action.group_ids` and excludes Portal Employee.

## Preservation

No persistent/transient model is added, removed, merged or moved. No field, method, route,
workflow, request type/stage seed, cron, ACL, record rule, dependency, integration contract,
history behavior, company boundary, portal trust boundary or enterprise UI capability is
removed or weakened. No sibling OneHR source is changed.

## Status

`NEW_BOUNDED_TASK_ATTEMPT: 1/2`  
`SOURCE_REVALIDATION: PASS`  
`SOURCE_ACCEPTANCE_PASS_COUNT: 112`  
`SOURCE_ACCEPTANCE_WARN_COUNT: 2`  
`SOURCE_ACCEPTANCE_FAIL_COUNT: 0`  
`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`  
`ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY: NO`

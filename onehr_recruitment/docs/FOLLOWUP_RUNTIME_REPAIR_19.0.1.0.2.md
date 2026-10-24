# OneHR Recruitment — Reviewer-Authorized Follow-up Runtime Repair 19.0.1.0.2

TASK: `ONEHR-RECRUITMENT-FOLLOWUP-PREBOARDING-SEARCH-20260903`  
ATTEMPT: `1 / 2` for this explicitly reviewer-authorized follow-up task  
PREVIOUS_TASK_STOP: `STOP_REASON: MAX_ATTEMPTS_REACHED`  
TARGET_ADDON: `onehr_recruitment`  
TARGET_PLATFORM: Odoo 19 Community Edition (`19.0.20251217`)  
WRITE_SCOPE: `onehr_recruitment` only  
ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`

## Reviewer authorization

After the prior Recruitment task reached its two-attempt ceiling, the reviewer explicitly
authorized a new bounded follow-up task limited to the proven Preboarding search-view defect
and its regression gate. This file records that new authorization boundary; it is not an
automatic third retry of the prior task.

## Concrete runtime evidence

Odoo reached `views/preboarding_views.xml` and rejected the `pending_tasks` search filter:

`Unsearchable field “checklist_pending_task_count” ...`

The field `onehr.preboarding.checklist_pending_task_count` is a display-only related counter
to `checklist_instance_id.pending_task_count` and is not stored/searchable.

## Bounded correction

The business meaning “Preboarding records with at least one pending checklist task” is
preserved by replacing only the filter domain:

- old: `[('checklist_pending_task_count', '>', 0)]`
- new: `[('checklist_instance_id.task_ids.state', '=', 'pending')]`

The new domain follows the canonical checklist instance → checklist task relation and filters
the task's stored lifecycle state. No counter field, model, workflow, security rule, ACL,
dependency, ownership boundary, or enterprise feature is changed.

## Regression prevention

`tools/source_acceptance.py` now:

1. requires exactly one `pending_tasks` Preboarding filter;
2. requires the exact searchable relational domain above; and
3. rejects any Preboarding XML domain that filters `checklist_pending_task_count`.

## Release marker

Previous version: `19.0.1.0.1`  
Follow-up repair version: `19.0.1.0.2`

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST`  
`ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO`

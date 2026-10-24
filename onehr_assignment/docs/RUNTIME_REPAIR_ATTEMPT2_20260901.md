
﻿# OneHR Assignment — Runtime Repair Attempt 2/2

TASK: ONEHR-ASSIGNMENT-DIRECT-FULL-RUNTIME-20260901
ATTEMPT: 2 / 2
TARGET_ADDON: onehr_assignment
WRITE_SCOPE: onehr_assignment only
ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE

## Concrete runtime evidence

Odoo 19 rejected the inherited Employee form view with:

View inheritance may not use attribute 'string' as a selector.

The failing source used:

- //page[@name='onehr_corehr_profile']//group[@string='Current Versioned Classification']

The same target file also contained the same compatibility pattern:

- //page[@string='Authorized Capacity']

Both occurrences are repaired in this single bounded attempt because
MAX_REPEAT_OF_SAME_ROOT_CAUSE=1.

## Architecture-preserving repair

- Employee extension now anchors after field onehr_primary_position_id.
- Position extension now anchors the parent page by its stable owned fields
  uthorized_fte and uthorized_headcount.
- No model, field, method, workflow, ACL, record rule, dependency, owner,
  effective-dating behavior, report, action, or enterprise feature is removed.
- Manifest version: 19.0.1.0.0 -> 19.0.1.0.1.
- Source acceptance now rejects any inherited XPath selector containing @string.

## Runtime state

WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST
ONEHR_ASSIGNMENT_MOVE_FORWARD_READY: NO

If this Attempt 2 fails again, do not perform another automatic source retry.
Classify the new failure first and enforce the root guardrail stop policy.

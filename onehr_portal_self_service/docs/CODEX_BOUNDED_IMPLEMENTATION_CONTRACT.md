
# OneHR Portal Self-Service — Codex Bounded Implementation Contract

ROLE = BOUNDED_IMPLEMENTATION_WORKER
ARCHITECTURE_AUTHORITY = NONE
SIMPLIFICATION_AUTHORITY = NONE
DELETION_AUTHORITY = NONE
MODEL_OWNERSHIP_CHANGE_AUTHORITY = NONE
DEPENDENCY_CHANGE_AUTHORITY = NONE
MAX_ATTEMPTS = 2
MAX_REPEAT_OF_SAME_ROOT_CAUSE = 1
TARGET_ADDON = onehr_portal_self_service
WRITE_SCOPE = onehr_portal_self_service/**
PRESERVATION_REQUIRED = YES
FUNCTIONAL_COMPLETENESS_REQUIRED = YES
STOP_ON_ARCHITECTURE_AMBIGUITY = YES
STOP_ON_REPEAT_ROOT_CAUSE = YES

Codex may diagnose a concrete defect and implement the smallest architecture-preserving
correction. It may not delete functions, widen ACL, replace owner models, add/remove hard
dependencies, edit sibling addons, mute tests or repeatedly retry the same failure.

The original Direct Full Build task reached its two-attempt limit after the
`portal.group_portal` → `base.group_portal` runtime correction and is closed.

On 2026-08-29 the reviewer explicitly approved a NEW bounded repair task:
`ONEHR-PORTAL-RUNTIME-REPAIR-20260829-B`. Attempt 1/2 is limited to the proven Odoo 19
`ir.actions.act_window.groups_id` → `group_ids` compatibility defect, its regression
prevention, and target-local evidence. This new authorization does not grant architecture,
simplification, sibling-edit or unlimited-retry authority.


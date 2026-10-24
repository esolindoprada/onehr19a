# OneHR Portal Self-Service — Scope Isolation Report

TASK_ID: `ONEHR-PORTAL-RUNTIME-REPAIR-20260829-B`
TASK: Explicitly approved new bounded runtime activation repair
ATTEMPT: 1/2
WRITE_SCOPE: `onehr_portal_self_service` only
LATEST_WORKSPACE_DUMP: `onehr19a(20260829-052556).md`
LATEST_WORKSPACE_DUMP_SHA256: `ba998fa30db8eb4dd2da5466cb20f804e9abb263a196793c78ac576a110606ee`
ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE

The latest supplied workspace proves a concrete Odoo 19 activation failure inside the target
addon only: `ir.actions.act_window` does not accept `groups_id`. The failing source is the
Bulk Request Decision bound action in `views/wizard_views.xml`.

The previous bounded task is retained as historical evidence and is not silently extended.
The reviewer explicitly opened this new bounded task after the prior task stopped at its
two-attempt limit.

No sibling OneHR addon source file is emitted or modified by this package.

SCOPE_ISOLATION_RESULT: PASS_SOURCE

## Files intentionally changed in this new task, Attempt 1

Runtime correction:
- `views/wizard_views.xml` — `groups_id` → `group_ids` on the bound window action only
- `__manifest__.py` — release `19.0.1.0.2`

Regression prevention:
- `tests/test_security.py` — test 34 for runtime action group membership
- `tools/source_acceptance.py` — reject `groups_id` on `ir.actions.act_window`; require `group_ids`; count ACL rows robustly despite blank lines

Evidence/documentation:
- `README.md`
- `docs/BOUNDED_RUNTIME_REPAIR_TASK_20260829_ATTEMPT_1.md`
- `docs/CODEX_BOUNDED_IMPLEMENTATION_CONTRACT.md`
- `docs/ENTERPRISE_COMPLETENESS_MATRIX.md`
- `docs/IMPLEMENTATION_REPORT.md`
- `docs/SCOPE_ISOLATION_REPORT.md`
- `docs/SOURCE_ACCEPTANCE_REPORT.txt`
- `docs/SOURCE_FINGERPRINT_SHA256.txt`
- `docs/WINDOWS_RUNTIME_ACCEPTANCE.md`

No model/business-workflow/controller/ACL/record-rule/data/seed file is otherwise changed.

## Baseline preservation comparison

Compared with the exact target-addon extraction from `onehr19a(20260829-052556).md`:

- baseline target files: 55
- existing files changed intentionally: 12
- new evidence files added: 1
- baseline files removed: 0

All runtime/business files outside the explicitly listed repair scope remain byte-identical
to the latest supplied target-addon baseline.

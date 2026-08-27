# OneHR Appraisal — Windows Runtime Acceptance Checklist

Source/static PASS is not runtime completion.

1. Back up the database and old `onehr_appraisal` folder.
2. Replace the old tutorial scaffold with this complete addon folder; do not merge.
3. Restart Odoo and Update Apps List.
4. Install `OneHR Appraisal` once; capture the FIRST traceback if it fails.
5. Verify `onehr_corehr` and `onehr_security` load first and no extra hard dependency appears.
6. Verify exactly the three Appraisal business models are registered; tutorial model absent.
7. Run all 24 post-install tests in a disposable database.
8. Verify Participant own/peer scope.
9. Verify Manager assigned-team scope and denial on another manager's team.
10. Verify Appraisal HR company-wide scope and multi-company isolation.
11. Cycle: create → KPI import → Generate Forms → Open Cycle.
12. Self/Manager/Peer ratings: entry → submit → evidence lock → score calculation.
13. Form: Draft → In Review → Consolidation → Closed → acknowledgement.
14. Verify rating distribution Pivot/Graph and Cycle Kanban/Calendar.
15. Render Appraisal PDF under permitted/denied users.
16. Run deadline reminder cron and verify duplicate activities are not produced.
17. If Learning is installed, test development hand-off under Learning authority.
18. If Analytics/Career/Portal/API modules are installed, exercise service contracts.
19. Run upgrade with `-u onehr_appraisal --stop-after-init`.
20. Verify post-upgrade smoke, data preservation and uniqueness constraints.
21. Compare exact Model Registry ED rows against Master Model Registry v1.
22. Only then may Appraisal be marked frozen/move-forward ready.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_APPRAISAL_MOVE_FORWARD_READY: NO

## Attempt 1 activation evidence

Attempt 1 failed during Python model import before registry completion:

`NotImplementedError: Compute method cannot depend on field 'id'.`

Repair package `19.0.1.0.1` is Attempt 2/2 and must be re-tested from the first
activation step. Another failure must be captured and classified; no automatic
third source mutation is allowed.

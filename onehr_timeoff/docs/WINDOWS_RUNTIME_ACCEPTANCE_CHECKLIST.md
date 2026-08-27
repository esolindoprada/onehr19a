# onehr_timeoff — Windows/Odoo 19 Runtime Acceptance Checklist

Run on the actual OneHR Windows Odoo 19 environment and a disposable validation database before declaring the addon frozen/move-forward-ready.

1. Confirm accepted hard dependencies are installed: `onehr_corehr`, `onehr_security`, `onehr_workflow_approval`.
2. Confirm no unapproved sibling folder was modified; replace only the target `onehr_timeoff` folder.
3. Update Apps List and install `OneHR Time Off` fresh. No registry, field, access, report or view error is allowed.
4. Run `--test-tags /onehr_timeoff`; expected source inventory is **20 runtime test methods**.
5. Upgrade once, rerun tests, then upgrade a second time to prove XML/data/cron idempotency.
6. UAT Leave Type: activate policy; verify active policy facts are frozen; create a non-overlapping successor version when policy changes.
7. UAT eligibility: grade, minimum service, first-year proration, seniority bonus, accrual cap.
8. UAT accrual scheduler: monthly/annual credit; rerun same day/period and verify no duplicate due to `source_key`.
9. UAT carry-over: prior-year residual → capped current-year carry-over with expiry; rerun and verify idempotency.
10. UAT opening balance: import CSV to allocation records as Draft, review, then Confirm; verify balance.
11. UAT mass allocation: modal batch → generate eligible employee child allocations → verify persistent batch/child audit and row buttons.
12. UAT employee request: own request only, working-calendar duration, half-day, attachment requirement, notice and max-duration validation.
13. UAT balance: insufficient entitlement rejected; approved request freezes allocation usage; cancellation releases reservation without deleting evidence.
14. UAT manager: direct-report visibility and team calendar only; unrelated employee requests/allocations remain invisible.
15. UAT HR: allowed-company policy/allocation/request access; cross-company denial for a user lacking that company.
16. UAT approval: configure a `onehr_workflow_approval` Time Off rule; submit → manager/approved path → request state Approved; reject path → Rejected; reset works.
17. UAT team conflict: warning mode posts warning; block mode rejects request above concurrent team threshold.
18. UAT soft Attendance integration: with Attendance installed, verify its approved extension hooks do not introduce reverse dependency and can reject conflicting shift schedules if configured.
19. UAT payroll payload: approved paid and unpaid leave return the expected downstream payload without creating payroll-owned records.
20. Verify Calendar/Pivot/Graph, statusbars, smart buttons, body actions, generated One2many row actions, chatter and PDF report.
21. Verify Time Off User sees the OneHR menu without receiving broad HR employee access.
22. Run cross-addon smoke/regression with the currently accepted OneHR suite.
23. Compare the three Time Off model names and exact effective-dating classifications against the authoritative OneHR Master Model Registry v1 before final freeze.

Required final evidence:

- FRESH_INSTALL: PASS
- TESTS_20: PASS
- FIRST_UPGRADE: PASS
- REPEAT_UPGRADE: PASS
- SECURITY_UAT: PASS
- ACCRUAL_CARRYOVER_UAT: PASS
- REQUEST_APPROVAL_BALANCE_UAT: PASS
- TEAM_CALENDAR_UAT: PASS
- MASS_ALLOCATION_UAT: PASS
- SOFT_INTEGRATION_UAT: PASS
- CROSS_ADDON_REGRESSION: PASS
- REGISTRY_ED_CLASSIFICATION_CHECK: PASS
- ENTERPRISE_COMPLETENESS_MATRIX: ALL_APPLICABLE_PASS

Only then: `ONEHR_TIMEOFF_MOVE_FORWARD_READY: YES`.

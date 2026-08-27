# onehr_payroll_bridge — Windows/Odoo 19 Runtime Acceptance Checklist

Use a disposable validation database before declaring move-forward readiness.

1. Verify accepted `onehr_corehr` and `onehr_security` versions are installed.
2. Update Apps List and install `OneHR Payroll Bridge` fresh.
3. Run `--test-tags /onehr_payroll_bridge`.
4. Verify Payroll Officer cannot modify configuration/post/reconcile and Payroll Manager can.
5. Verify a user without Payroll groups cannot browse payroll bridge records.
6. Verify allowed-company isolation for Config/Export/Import.
7. Create a CSV/manual configuration; validate mapping and structure maps.
8. Generate an Export with multiple employees; verify employee scope, CSV content,
   source/config snapshot, SHA-256 and all source totals.
9. If Attendance is installed, verify only accepted/posted attendance and approved/export-ready
   overtime contribute according to configuration.
10. If Time Off is installed, verify approved/done paid/unpaid leave is period-bounded correctly.
11. If Assignment is installed, verify effective costing dimensions are included without modifying
    Assignment evidence.
12. Post the export; verify source period/scope/evidence becomes immutable.
13. Import vendor CSV; test resolved and unresolved employee numbers, unknown currency and mapping errors.
14. Validate current vendor results; test optional net-equation tolerance.
15. Create a correction revision; verify prior row becomes Superseded and cannot be edited.
16. Reconcile; verify full-reconciliation policy, final import state, department costing payload,
    reconciliation coverage and time-to-close.
17. Print Payroll Reconciliation Record and inspect sensitive-data visibility.
18. Test monthly scheduler; it may create Draft batches but must never auto-post or auto-reconcile.
19. Upgrade once and rerun tests.
20. Upgrade a second time to verify XML/data idempotency.
21. Test uninstall/reinstall on a disposable DB; production history guards must not block uninstall.
22. Run cross-addon regression with current accepted OneHR suite.
23. Compare exact Master Model Registry rows/ED labels; do not infer them.

Required final evidence:

- `REGISTRY_ED_ALIGNMENT: PASS`
- `FRESH_INSTALL: PASS`
- `RUNTIME_TESTS: PASS`
- `SECURITY_UAT: PASS`
- `CSV_ROUNDTRIP_UAT: PASS`
- `RECONCILIATION_UAT: PASS`
- `REVISION_HISTORY_UAT: PASS`
- `OPTIONAL_SOURCE_INTEGRATION_UAT: PASS`
- `FIRST_UPGRADE: PASS`
- `REPEAT_UPGRADE: PASS`
- `UNINSTALL_REINSTALL: PASS`
- `CROSS_ADDON_REGRESSION: PASS`
- `ENTERPRISE_COMPLETENESS_MATRIX: ALL_APPLICABLE_PASS`

Only then:

`ONEHR_PAYROLL_BRIDGE_MOVE_FORWARD_READY: YES`

# onehr_payroll_l10n_id — Windows/Odoo 19 Acceptance Checklist

Use a disposable validation database before declaring final/frozen.

1. Confirm accepted `onehr_payroll_bridge` is installed.
2. Update Apps List and install `OneHR Payroll Localization Indonesia` fresh.
3. Run `--test-enable --test-tags /onehr_payroll_l10n_id --stop-after-init`.
4. Verify plain internal users cannot read localization parameters.
5. Verify Payroll Officer can read but cannot create/write/delete.
6. Verify Payroll Manager can administer unused versions.
7. Verify cross-company isolation.
8. Create a parameter bundle with a valid effective date.
9. Review PPh21/PTKP/TER values against current deployment regulation.
10. Review BPJS Kesehatan rates/floor/ceiling.
11. Review BPJS Ketenagakerjaan rates and **current JP wage ceiling/effective date**.
12. Review THR policy/calendar.
13. Run Validate Parameter Structure.
14. Confirm an unreviewed version blocks Payroll Export generation.
15. Mark Regulatory Review Complete.
16. Generate Payroll Export and verify:
    - parameter binding;
    - full localization snapshot;
    - localization SHA-256;
    - employee row localization code/revision/hash;
    - base Payroll Bridge source SHA remains present.
17. Reset generated package and verify localization evidence clears.
18. Generate again, then verify a used parameter cannot be edited.
19. Create New Version; verify predecessor closes one day before new effective date.
20. Verify predecessor statutory SHA remains stable after governed period closure.
21. Create a Correction Revision and verify prior version remains preserved/inactive.
22. Export JSON and CSV; inspect data.
23. Import each supported format as a future unreviewed new version.
24. Print Indonesia Payroll Parameter Record.
25. Verify Payroll Bridge adapter payload includes top-level `indonesia_localization`.
26. Upgrade once and rerun tests.
27. Upgrade again for idempotency.
28. Uninstall/reinstall on disposable DB.
29. Run cross-addon regression with accepted OneHR suite.
30. Compare exact Master Model Registry row/ED classification.

Required final evidence:

- `REGISTRY_ED_ALIGNMENT: PASS`
- `CURRENT_REGULATORY_REVIEW: PASS`
- `FRESH_INSTALL: PASS`
- `RUNTIME_TESTS: PASS`
- `SECURITY_UAT: PASS`
- `EFFECTIVE_DATE_HISTORY_UAT: PASS`
- `JSON_CSV_ROUNDTRIP_UAT: PASS`
- `PAYROLL_BRIDGE_LOCALIZATION_UAT: PASS`
- `REPORT_BROWSER_UAT: PASS`
- `FIRST_UPGRADE: PASS`
- `REPEAT_UPGRADE: PASS`
- `UNINSTALL_REINSTALL: PASS`
- `CROSS_ADDON_REGRESSION: PASS`
- `ENTERPRISE_COMPLETENESS_MATRIX: ALL_APPLICABLE_PASS`

Only then:

`ONEHR_PAYROLL_L10N_ID_MOVE_FORWARD_READY: YES`

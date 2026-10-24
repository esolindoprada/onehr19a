
# onehr_assignment — Windows/Odoo 19 Runtime Acceptance Checklist

Run on the real OneHR Windows Odoo 19 environment and a disposable validation database before declaring move-forward readiness.

1. Confirm accepted dependencies are installed: `onehr_base`, `onehr_corehr`, `onehr_security`, `onehr_workflow_approval`.
2. Update Apps List; install `OneHR Assignment` fresh. No registry/view/security error is allowed.
3. Run module tests with post-install tag `onehr_assignment`; expected source inventory is **26 test methods**.
4. Upgrade once and run the same tests; upgrade a second time to detect non-idempotent XML/data changes.
5. UAT primary assignment: approval → activation → correct `hr.version` job/department/location/grade/primary-position sync and direct manager.
6. UAT secondary assignment: activate without overwriting canonical primary placement.
7. UAT overlap/FTE/capacity: reject duplicate overlapping primary, employee FTE >1, Position HC/FTE over-capacity and budget-interval over-capacity.
8. UAT movement: direct-report proposer → approval → manager execution; verify immutable source history, successor link, future-dated Approved successor and due activation.
9. UAT costing: 100% effective split accepted; gap/over-allocation/frozen-history edits rejected.
10. UAT workforce planning: versioning, approval, activation and Position Budget materialization/capacity control.
11. UAT security: proposer cannot browse unrelated/private assignment data; Officer cannot cross company; UI buttons do not grant authority beyond ACL/rules/model checks.
12. Verify List/Form/Search for all seven custom models plus Calendar/Pivot/Graph/report surfaces.
13. On a disposable DB, uninstall `onehr_assignment` after creating governed history, verify uninstall is not blocked by business ondelete guards, then reinstall and rerun tests.
14. Run cross-addon smoke/regression with currently accepted OneHR suite.

Required final evidence:

- FRESH_INSTALL: PASS
- TESTS_26: PASS
- FIRST_UPGRADE: PASS
- REPEAT_UPGRADE: PASS
- SECURITY_UAT: PASS
- MOVEMENT_UAT: PASS
- CAPACITY_COSTING_UAT: PASS
- WORKFORCE_UAT: PASS
- UNINSTALL_REINSTALL: PASS
- CROSS_ADDON_REGRESSION: PASS
- ENTERPRISE_COMPLETENESS_MATRIX: ALL_APPLICABLE_PASS

Only then: `ONEHR_ASSIGNMENT_MOVE_FORWARD_READY: YES`.

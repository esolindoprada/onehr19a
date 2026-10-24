# Windows Runtime Acceptance

Do not convert source PASS into runtime PASS. On the target Windows Odoo 19 environment:

1. Replace the entire old `onehr_retirement_offboarding` folder; do not merge scaffold files.
2. Restart Odoo and Update Apps List.
3. Install the addon on a disposable/fresh acceptance database.
4. Confirm all dependencies install and all menus/views/reports load.
5. Run tagged post-install tests for `onehr_retirement_offboarding`.
6. Test Task Owner, Officer, Manager and Administrator roles across two companies.
7. Configure an Offboarding Workflow Approval rule and test approve/reject/cancel behavior.
8. Generate clearance tasks; test row actions, SLA reminders and asset-return evidence.
9. Test exit-interview schedule/submit/waive/reopen and both reports.
10. Test access revocation with Offboarding Admin alone (must fail) and with System Administrator additionally (must succeed); verify self-revoke is blocked.
11. When `onehr_employment_contract` is installed, test normal-ACL termination delegation and closure gate.
12. When Payroll/Document/Portal/API/Analytics/Branch are installed, perform contract smoke tests without granting this addon ownership of those domains.
13. Repeat install/upgrade as applicable and verify no structural loss.

If a failure occurs, capture the **FIRST complete traceback**. Classify it as addon source, dependency, environment or harness failure before any code mutation.

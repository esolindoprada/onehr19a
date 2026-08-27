# OneHR Discipline — Windows Runtime Acceptance

Source/static PASS is not runtime completion.

1. Back up the database and current `onehr_discipline`.
2. Replace the tutorial scaffold completely; do not merge old controller/demo/tutorial files.
3. Restart Odoo and Update Apps List.
4. Install OneHR Discipline once; preserve the FIRST complete traceback if it fails.
5. Verify hard dependencies load exactly CoreHR + Security + Workflow Approval.
6. Verify only `onehr.discipline.case` and `onehr.discipline.sanction` register as new persistent Discipline models.
7. Inspect physical tables, indexes, relation tables and constraints for HARD GATE 11.
8. Run all 50 post-install tests in a disposable database.
9. Confirm a plain HR user without Discipline role cannot access cases.
10. Confirm Investigator sees only assigned/owned cases and cannot reclassify/decide.
11. Confirm HRBP sees assigned/owned cases and can progress/create sanctions.
12. Confirm Manager/Legal company scope and cross-company denial.
13. Create active Workflow Approval rules for each sanction type/risk combination used in UAT.
14. Create a case and verify standardized `DISC/...` reference.
15. Progress Reported → Under Investigation; verify SLA/activity.
16. Record evidence/findings and schedule hearing.
17. Print Hearing Summons and queue hearing notice.
18. Progress to Hearing; record employee/witness statements and minutes.
19. Print Hearing Minutes.
20. Progress to Decision and create written warning/SP sanction.
21. Submit sanction; verify Workflow request routing/approval evidence.
22. Approve through a configured eligible approver.
23. Execute/issue sanction; verify Workflow request becomes Executed only after source execution.
24. Record employee service/receipt and print sanction letter.
25. Exercise SP-1/SP-2/SP-3, suspension, probation and last-chance terms.
26. Exercise payroll-deduction request with a configured approval rule.
27. Verify Payroll payload contains only executed approved Discipline requests.
28. Record Payroll adapter callback without any Discipline payroll calculation/posting.
29. Exercise contract probation/termination handoff payload without contract mutation.
30. Exercise employee appeal → Legal review → upheld/modified/overturned result.
31. Confirm active appeal blocks case closure.
32. Close no-action case and formal-sanction case.
33. Verify retention date, immutable history and repeat-offense indicator.
34. Run SLA cron twice and verify activities are not duplicated.
35. Render Case Outcome PDF.
36. Render Outcome & Lead-Time Register PDF.
37. Render Decision Record PDF.
38. Verify Case/Sanction Pivot and Graph views.
39. If Appraisal is installed and caller has Appraisal HR, refresh accepted discipline evidence.
40. If PnP is installed and caller has PnP access, open the soft policy reference.
41. Exercise restricted Document handoff payload.
42. Exercise Analytics/API KPI snapshot.
43. Run `-u onehr_discipline --stop-after-init`.
44. Repeat upgrade/idempotency and post-upgrade smoke.
45. Compare exact Master Model Registry ED rows when authoritative rows are available.
46. Verify no sibling OneHR source was modified.
47. Only after every applicable gate passes may the addon be frozen.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_DISCIPLINE_MOVE_FORWARD_READY: NO

## Runtime Attempt 1 activation evidence — 2026-08-24

Activation reached:

`views/discipline_case_views.xml`

Odoo rejected Search filter `Repeat Offense` because the computed/non-stored
`repeat_offense` field had no search method.

Classification:

`ADDON_SOURCE_FAILURE`

Repair package `19.0.1.0.1` adds an explicit `_search_repeat_offense` method and
a source-acceptance regression gate. Re-run activation from step 4 using the
complete repaired addon folder.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST_AFTER_ATTEMPT_1`

A subsequent failure must be captured as the FIRST complete traceback and
classified before any Attempt 2 source change.

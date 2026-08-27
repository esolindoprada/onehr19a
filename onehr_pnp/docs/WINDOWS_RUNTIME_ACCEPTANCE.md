# OneHR PnP — Windows Runtime Acceptance Checklist

Source/static PASS is not runtime completion.

1. Backup the database and current `onehr_pnp`.
2. Replace the tutorial scaffold completely; do not merge old controller/demo/tutorial files.
3. Restart Odoo and Update Apps List.
4. Install `OneHR Policies & Procedures` once; preserve the FIRST complete traceback if it fails.
5. Verify hard dependencies load exactly Security + Document + Workflow Approval.
6. Verify exactly `onehr.policy`, `onehr.policy.ack`, `onehr.policy.evidence` register.
7. Verify Settings extension appears and no fourth PnP persistent model is created.
8. Inspect physical table/index/relation/constraint names for HARD GATE 11.
9. Run all 47 post-install tests in a disposable database.
10. Confirm plain internal user has no PnP model access.
11. Confirm Reader sees only assigned Published/Review/Archived policy history and own ack/evidence.
12. Confirm Owner sees own Draft/approval/version set, not company-wide employee evidence.
13. Confirm Compliance company scope and multi-company denial.
14. Configure active internal/confidential OneHR Document archive category.
15. Configure active Workflow Approval rule for `onehr.policy` and required route.
16. Create policy → audience → Preview Audience → Submit for Approval.
17. Approver finalizes Workflow request; verify source Policy becomes Approved.
18. Publish; verify Document snapshot is Issued, assignments generated, request becomes Executed.
19. Employee reads and acknowledges; verify timestamp/source.
20. Employee submits attachment/photo/link/note evidence; Compliance verifies/rejects.
21. Verify unit evidence and policy-wide evidence coverage.
22. Verify acknowledgement and evidence KPIs.
23. Start periodic Review; complete unchanged and verify next review date.
24. Create controlled revision; approve/publish successor.
25. Verify prior current version becomes Archived, old ack/evidence retained, Document header reused.
26. Queue publication notices and acknowledgement reminders.
27. Run daily cron twice; verify review/reminder activities are throttled and not duplicated.
28. Render Policy PDF.
29. Render Policy Compliance Summary.
30. Render Review/Expiry Register.
31. Render Evidence Coverage Register.
32. Exercise Portal policy payload as assigned and unassigned users.
33. Exercise evidence submission model service.
34. Exercise API acknowledgement status as self and Compliance.
35. Exercise Analytics compliance snapshot.
36. If OneHR SOP is installed, verify related SOP resolution honors SOP's own security.
37. If Branch extension is installed, verify branch audience resolution contract.
38. Test restricted Document category denial unless explicit Document Compliance is granted.
39. Run `-u onehr_pnp --stop-after-init`.
40. Repeat upgrade/idempotency and post-upgrade smoke.
41. Compare exact Master Model Registry ED rows.
42. Verify sibling OneHR source unchanged.
43. Only after every applicable gate passes may the addon be frozen.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_PNP_MOVE_FORWARD_READY: NO

# OneHR SOP — Windows Runtime Acceptance Checklist

1. Back up database and old `onehr_sop`.
2. Replace the tutorial scaffold completely; do not merge old controllers/demo/views.
3. Restart Odoo; Update Apps List.
4. Install `OneHR SOP` once and preserve the first complete traceback if it fails.
5. Verify hard dependency graph shows only `onehr_security` + `onehr_document`.
6. Verify exactly `onehr.sop`, `onehr.sop.version`, `onehr.sop.ack` register.
7. Inspect tables/M2M/constraints for HARD GATE 11 identifier safety.
8. Run all 40 post-install tests in a disposable database.
9. Confirm plain internal users have no SOP model access.
10. Confirm SOP Reader sees only assigned current Published SOP and own Ack.
11. Confirm QA/Editor/Approver company isolation.
12. Create Document category for SOP archive.
13. Create SOP → Draft V1 → target department/job/employee → Preview Audience.
14. Submit Review → Approve → Publish.
15. Confirm generated Ack rows equal resolved active audience.
16. Confirm OneHR Document archive header/version is created and version is Issued.
17. Employee opens SOP and executes Read & Agree; verify timestamp/source.
18. Publish V2; confirm V1 becomes Obsolete and archive header is reused.
19. Confirm V1 acknowledgements remain historical and undeletable.
20. Verify acknowledgement rate and days-to-90%.
21. Queue publication notice and acknowledgement reminders.
22. Run daily cron twice; verify review/reminder activities do not duplicate for same due event.
23. Export Ack CSV and inspect UTF-8 content.
24. Render SOP PDF.
25. Render compliance PDF.
26. Render review/expiry register.
27. Exercise Portal payload under assigned and unassigned users.
28. Exercise API status model service under self and Approver authority.
29. Exercise Analytics KPI snapshot.
30. Verify multi-company denial.
31. Run `-u onehr_sop --stop-after-init`.
32. Repeat upgrade/idempotency and post-upgrade smoke.
33. Compare exact Master Model Registry ED rows.
34. Verify no sibling addon source changed.
35. Only after every applicable gate passes may the addon be frozen.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_SOP_MOVE_FORWARD_READY: NO

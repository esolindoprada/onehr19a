
# OneHR Job Description — Windows Runtime Acceptance Checklist

Source/static PASS is not runtime completion.

1. Back up the database and existing `onehr_job_description`.
2. Replace the tutorial scaffold completely; do not merge old controllers/demo/views.
3. Restart Odoo and Update Apps List.
4. Install `OneHR Job Description` once and capture the first complete traceback on failure.
5. Verify only hard dependencies `onehr_base` and `onehr_security`.
6. Verify exactly `onehr.jd` and `onehr.jd.version` register; tutorial model absent.
7. Inspect PostgreSQL/Odoo registry table names and HARD GATE 11 identifier safety.
8. Run all 30 post-install tests in a disposable database.
9. Verify ordinary internal users have no JD model access.
10. Verify JD Reader sees current published content only.
11. Verify Editor/Approver/Admin company isolation and assigned approval matrix.
12. Create a JD per canonical OneHR position.
13. Create and publish a job-family template; generate position JDs.
14. Exercise Draft → Review → Approved → Published.
15. Publish V2; confirm V1 remains historical and V2 is the only current version.
16. Verify approved/published content and identity locks.
17. Verify KPI/competency/qualification/HSE/K3 content and fingerprint.
18. Import `.txt`, `.md`, `.html` and `.docx` source documents.
19. Render current JD PDF, comparison PDF and JD register.
20. Run daily governance cron; verify version age/review overdue and no duplicate activities.
21. With Career installed and authorized, refresh position competency snapshot.
22. Exercise Recruitment/Appraisal/Portal/API service contracts where downstream addons are installed.
23. Verify KPI snapshot coverage and average version age.
24. Run first upgrade: `-u onehr_job_description --stop-after-init`.
25. Run repeated upgrade/idempotency and post-upgrade smoke.
26. Compare exact Master Model Registry ED rows.
27. Verify no sibling OneHR addon source changed.
28. Only after all applicable gates pass may Job Description be marked frozen.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_JOB_DESCRIPTION_MOVE_FORWARD_READY: NO


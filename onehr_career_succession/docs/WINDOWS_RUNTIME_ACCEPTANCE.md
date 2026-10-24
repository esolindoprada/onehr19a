
# OneHR Career & Succession — Windows Runtime Acceptance Checklist

Source/static PASS is not runtime completion.

1. Backup database and old `onehr_career_succession`.
2. Replace the old scaffold completely; do not merge tutorial files.
3. Restart Odoo and Update Apps List.
4. Install `OneHR Career & Succession` once; capture the first full traceback if it fails.
5. Verify only hard dependencies `onehr_base` and `onehr_corehr`.
6. Verify exactly four persistent Career/Succession models register.
7. Run all 26 post-install addon tests in a disposable database.
8. Verify ordinary internal users have no custom-model access.
9. Verify HRBP and Talent Manager roles under company isolation.
10. Competency: create/edit/archive, level-scale validation and native CSV import.
11. Position Competency: required-level validation, duplicate prevention, matrix Pivot/Graph.
12. Talent: Draft → Proposed → Approved → Active → Inactive.
13. Verify high-potential, 9-box, readiness score/level and retention risk.
14. Verify target competency requirements and gap-analysis PDF.
15. Verify Succession Plan: Draft → Proposed → Approved → Active → Closed.
16. Verify multiple candidates, primary successor, coverage %, bench strength and risk index.
17. Run succession review reminder cron; verify no duplicate activities.
18. With Appraisal installed and authorized, refresh latest closed appraisal evidence.
19. With Learning installed and authorized, refresh learning completion evidence.
20. Exercise Analytics/Portal/API model-service contracts when downstream modules are available.
21. Render both QWeb PDFs under permitted/denied users.
22. Run first upgrade with `-u onehr_career_succession --stop-after-init`.
23. Run repeated upgrade/idempotency and post-upgrade smoke.
24. Compare exact Master Model Registry ED rows.
25. Verify no sibling addon source changed.
26. Only after all applicable gates pass may the addon be marked frozen.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_CAREER_SUCCESSION_MOVE_FORWARD_READY: NO


## 2026-09-10 bounded Users / Access Rights compatibility retest

1. Deploy both corrected owners together: `onehr_career_succession` and `onehr_pnp`.
2. Restart Odoo, Update Apps List, then upgrade both modules before testing the Users form.
3. Verify `onehr_career_succession.module_category_onehr_career_succession` resolves to `OneHR Career and Succession`.
4. Open **Settings → Users & Companies → Users**, then open at least two users.
5. Confirm the Access Rights tab renders without Owl/`parseXML` lifecycle error.
6. Change one non-sensitive OneHR group assignment, save, reopen the user, and confirm the same category hierarchy renders.
7. Run the addon post-install tests; the dynamic-category regression must pass across installed OneHR privilege categories.
8. Runtime PASS remains separate from source PASS.


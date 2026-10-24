
# OneHR Portal Self-Service — Windows Runtime Acceptance Checklist

Source/static PASS is not runtime completion.

1. Back up database and old `onehr_portal_self_service` folder.
2. Replace the old tutorial scaffold with this complete addon; do not merge tutorial files.
3. Restart Odoo 19 CE and Update Apps List.
4. Install `OneHR Portal Self-Service`; capture the FIRST complete traceback if it fails.
5. Verify hard dependencies load without adding optional OneHR addons as hidden hard dependencies.
6. Verify exactly the three persistent Portal business models register; tutorial model absent.
7. Run all 34 post-install tests in a disposable database.
8. Validate Portal Employee own-request access and denial of another employee's request.
9. Validate Portal Manager direct-report visibility/decision and denial on another manager's team.
10. Validate Portal HR company-wide scope and cross-company isolation.
11. Validate `/my/hr`, `/my/hr/new`, `/my/hr/<id>` and `/my/team` with browser CSRF/session behavior.
12. Create → Save Draft → Submit → Manager decision → HR decision → Processing → Done.
13. Test manager and HR rejection with mandatory reason and retained decision evidence.
14. Test SLA deadline, overdue search, reminder cron and duplicate-activity prevention.
15. Test portal comments/attachments, 10-file/10 MB-per-file/25 MB-total limits, and verify internal `mail.mt_note` chatter is never rendered to employee/manager portal users.
16. Test non-HR final approval with `auto_execute_on_approval=True`: approval must succeed, integration must remain Pending, and no downstream HR authority may be inherited.
17. Test Profile Change under Portal HR authority and whitelist enforcement.
18. With Time Off installed, test hand-off under a user who has both Portal HR and required Time Off authority.
19. With Learning installed, test accepted `onehr_external_enroll` hand-off under Learning authority.
20. With Document installed, test document/version creation under Document authority.
21. With Appraisal/Payroll/JD/PnP/SOP/Career installed, verify cards appear only when normal owner ACL permits.
22. Confirm confidential Discipline information does not appear in employee self-service.
23. Validate request Type/Stage backend forms, search/list, smart/body/row actions, Request Kanban/Calendar/Pivot/Graph.
24. Inspect PostgreSQL/Odoo registry identifiers for HARD GATE 11 naming safety.
25. Run `-u onehr_portal_self_service --stop-after-init` on a supported prior/deployed database.
26. Repeat upgrade/idempotency where applicable and verify no duplicate seed records/cron/actions.
27. Verify post-upgrade data preservation, references, SLA evidence and decision history.
28. Compare exact Master Model Registry ED rows with the implemented models.
29. Only after every applicable gate passes may this addon become frozen/move-forward ready.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY: NO

## Attempt 1 activation evidence / bounded repair Attempt 2

The first activation of release `19.0.1.0.0` failed while loading
`security/onehr_portal_security.xml`:

`ValueError: External ID not found in the system: portal.group_portal`

Release `19.0.1.0.1` is the bounded Attempt 2/2 correction and uses the Odoo 19 canonical
external ID `base.group_portal`.

Re-test from step 3 using this exact package. If another activation failure occurs, capture
the FIRST complete traceback and stop automatic source mutation under the current task.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY: NO


## Explicitly approved new bounded repair task — release 19.0.1.0.2

The next activation after `19.0.1.0.1` progressed further and failed while loading
`views/wizard_views.xml`:

`ValueError: Invalid field 'groups_id' in 'ir.actions.act_window'`

The reviewer explicitly authorized a NEW bounded repair task. Release `19.0.1.0.2` is
Attempt 1/2 of that new task and changes the field to Odoo 19 `group_ids` while retaining
Portal Manager and Portal HR restriction on the Bulk Request Decision action.

Re-test from step 3 using this exact package. If another activation failure occurs, capture
the FIRST complete traceback before any further source change; classify it against the new
task's remaining bounded attempt.

NEW_BOUNDED_TASK_ATTEMPT: 1/2  
WINDOWS_RUNTIME_ACCEPTANCE: PENDING  
ONEHR_PORTAL_SELF_SERVICE_MOVE_FORWARD_READY: NO

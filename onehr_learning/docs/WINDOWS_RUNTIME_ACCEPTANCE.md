# OneHR Learning — Windows Runtime Acceptance Checklist

Source/static PASS is not runtime completion.

Run on the user's actual Odoo 19 CE Windows environment:

1. Back up the database and current `onehr_learning` folder.
2. Replace the generic scaffold with this complete `onehr_learning` folder.
3. Restart Odoo and Update Apps List.
4. Fresh-install `onehr_learning`; capture the FIRST traceback if installation fails.
5. Verify the four hard dependencies are installed/loaded first.
6. Verify all eight model tables/registry entries exist and no tutorial model exists.
7. Verify menus open for L&D Officer, Trainer and Learning Manager Approver.
8. Verify company isolation and Trainer assigned-session rules, including a dual-role user.
9. Course: create → validate prerequisites → publish → unpublish.
10. Session: create → open → import participant CSV → start → complete; verify capacity/waitlist.
11. Enrollment: Request Approval → approve in workflow → Enroll/Waitlist → Attended →
    Passed/Failed → Certified; test rejection/reset/cancel.
12. Training Attendance: mark present/late/partial/absent/excused; verify completed evidence lock.
13. Certificate: issue → print PDF → expiry processing → revoke; test renewal reminder activity.
14. Budget/Cost: activate budget → planned → committed → actual; test block/warn overrun policy.
15. Optional installed integrations: Time Off, Attendance, Document, Payroll Bridge payload,
    Portal payload, Analytics snapshot, Integrations API service.
16. Run module tests in a disposable test database.
17. Upgrade the addon with `-u onehr_learning --stop-after-init`; verify no migration/registry error.
18. Compare the exact eight Registry rows and ED classifications against Master Model Registry v1.
19. Review UI manually: statusbars, smart buttons, row actions, search/group-by, lists,
    calendars, kanban, pivot/graph, chatter and access-denied behavior.
20. Only after all applicable gates pass may the addon be marked frozen/move-forward ready.

WINDOWS_RUNTIME_ACCEPTANCE: PENDING
MOVE_FORWARD_READY: NO

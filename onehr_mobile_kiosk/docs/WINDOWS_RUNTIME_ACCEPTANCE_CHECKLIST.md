# OneHR Mobile Kiosk — Windows Odoo 19 Runtime Acceptance Checklist

Run on the user's target Windows Odoo 19 environment. Source/static PASS does not satisfy this gate.

1. Fresh install `onehr_mobile_kiosk`.
2. Confirm only hard dependency `onehr_attendance` is pulled by this addon.
3. Run all 24 tagged runtime test methods.
4. Open Device List/Form/Search; exercise statusbar, smart buttons, body actions and One2many row actions.
5. Create dedicated Kiosk Operator user; register device; issue token; activate.
6. Verify operator sees only assigned device; Admin sees allowed-company devices.
7. Confirm old token fails after rotation and expired token fails.
8. Open authenticated kiosk URL; verify raw token never appears in URL.
9. QR/USB scanner identify + check-in creates canonical `hr.attendance`.
10. Check-out updates the same canonical open attendance.
11. Test NFC in a supported HTTPS/browser environment.
12. Test geolocation required, Warn and Block geofence scenarios.
13. Disconnect network; create attendance event; verify encrypted local queue; reconnect and sync.
14. Retry a controlled failed event; validate Failed → Synced or Dead Letter behavior.
15. Confirm raw token and scanned identifier do not appear in server kiosk evidence fields.
16. If `onehr_timeoff` is installed, link an employee self-service user and test leave balance + quick request.
17. Verify quick Time Off fails safely when the employee lacks self-service authority.
18. Render Kiosk Device Usage PDF.
19. Open Log Calendar/Pivot/Graph and validate latency/error analysis.
20. Cross-company negative tests.
21. First upgrade (`-u onehr_mobile_kiosk`) with existing device/log data.
22. Repeated upgrade with no duplicate XML IDs/sequences/cron or evidence loss.
23. Disposable-DB uninstall/reinstall validation.
24. Cross-addon regression: Attendance check-in/out/reconciliation and Time Off approval/balance unchanged.
25. Compare exact Master Model Registry rows/ED labels for `onehr.kiosk.device` and `onehr.kiosk.log`.

Final freeze requires every applicable item PASS.

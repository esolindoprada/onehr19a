# OneHR Attendance — Baseline Feature Preservation Matrix

| Baseline capability | Enterprise implementation | Status |
|---|---|---|
| Shift definitions | `onehr.shift` effective-dated policy with Odoo `resource.calendar` reference | PRESERVED + EXPANDED |
| Rotation / work patterns | Versioned `onehr.shift.pattern`, cycle tokens and pattern schedule | PRESERVED + EXPANDED |
| Calendar by location/position | Shift scope on Odoo work location / OneHR position, explicit employee schedule, calendar UI | PRESERVED + EXPANDED |
| Check-in/out | Canonical Odoo `hr.attendance`; no duplicate transaction | PRESERVED NATIVE-FIRST |
| Web/kiosk/mobile/device source | Source channel/system/reference/device metadata and adapter-safe ingestion service | PRESERVED |
| QR/NFC/mobile kiosk | Downstream `onehr_mobile_kiosk` remains owner; attendance exposes stable ingestion contract | PRESERVED AS SOFT INTEGRATION |
| Late / early leave | Planned-vs-actual analysis with separate grace periods and exception evidence | PRESERVED + HARDENED |
| Missing punches | Daily prior-day detection with ED3 missing-in/missing-out exception evidence | EXPANDED |
| Rounding | Policy-rounded hours stored separately; native `worked_hours` is never rewritten | PRESERVED SAFELY |
| Geofence | Optional shift-location radius + canonical punch coordinates; review evidence | EXPANDED |
| Overtime | Odoo 19 native overtime line/rule/ruleset remains authoritative; OneHR metadata added | PRESERVED NATIVE-FIRST |
| Payroll posting readiness | OneHR Confirmed → Posted business-readiness layer; native overtime approval must be resolved | PRESERVED WITHOUT PAYROLL OWNERSHIP |
| Time-off / training exclusions | Named extension hook on shift schedule; no reverse dependency or fake local leave/training model | PRESERVED AS EXTENSION CONTRACT |
| Fingerprint CSV | UTF-8 CSV batch, identifier mapping, timezone normalization, validation and idempotency | PRESERVED + HARDENED |
| Reconciliation | Persistent governed ED3 batch before canonical attendance creation | EXPANDED |
| Reports | Attendance PDF, reconciliation control PDF, pivot/graph/calendar/list analysis | PRESERVED + EXPANDED |
| KPI support | Late minutes, early minutes, rounded hours, review state, native overtime dimensions available to analytics | PRESERVED |
| Multi-company | Company ACL/rules and company integrity checks | PRESERVED + HARDENED |
| Branch | No reverse dependency; optional branch scope kept soft and owned by branch addon | PRESERVED BY ARCHITECTURE |
| API posting | `hr.attendance.onehr_ingest_interval()` service contract, no public controller in domain addon | PRESERVED BY ADAPTER BOUNDARY |
| Audit trail | Chatter/activity on OneHR models + immutable evidence/timestamps/users | PRESERVED + HARDENED |

No feature was removed merely to obtain installation or test PASS.

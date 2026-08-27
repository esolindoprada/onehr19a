# OneHR Mobile Kiosk — Baseline Feature Preservation Matrix

| Product baseline capability | Enterprise implementation | Status |
|---|---|---|
| Check-in/out | `hr.attendance.onehr_kiosk_apply_punch()` delegates new check-in to accepted `onehr_ingest_interval()` and closes the canonical open attendance for checkout | PRESERVED NATIVE-FIRST |
| QR | USB-scanner input + browser `BarcodeDetector` when available | PRESERVED + EXPANDED |
| NFC | Browser Web NFC `NDEFReader` when available | PRESERVED + EXPANDED |
| Geotag | Browser geolocation captured as attendance/log evidence | PRESERVED |
| Geofence | Device policy Ignore/Warn/Block using OneHR work-location coordinates | EXPANDED |
| Office/factory kiosk | Authenticated dedicated service-user kiosk web UI | PRESERVED |
| Face-ready | Capability flag only; no biometric storage or local face engine | PRESERVED SAFELY |
| Leave balance | Dynamic soft read of active OneHR Time Off policies/balances under employee self-service user | PRESERVED |
| Today's schedule | Reads accepted OneHR Attendance shift/schedule contract | PRESERVED |
| Quick Time Off | Dynamic `onehr_timeoff` create + submit under employee self-service user | PRESERVED |
| Device token | SHA-256 digest only; constant-time comparison; one-time raw display; expiry/rotation | PRESERVED + HARDENED |
| Online/offline queue | Encrypted browser queue + durable `onehr.kiosk.log` server queue | PRESERVED + HARDENED |
| Sync/retry | Queued → Processing → Synced/Failed/Blocked/Dead Letter with bounded backoff | PRESERVED + EXPANDED |
| Device usage report | Backend list/calendar/pivot/graph + QWeb device usage summary | PRESERVED + EXPANDED |
| Error rate / latency | Device error/queue counters and average sync latency | PRESERVED |
| Multi-company | ACL + global company rules + service-user device scope | PRESERVED + HARDENED |
| Branch optionality | No branch duplication or reverse dependency; company remains mandatory partition | PRESERVED |
| Third-party webhook | Explicitly remains `onehr_integrations_api` ownership | PRESERVED AS SOFT CONTRACT |
| Audit | Both persistent models inherit `onehr.mixin.audit`; processed evidence is protected | PRESERVED + HARDENED |

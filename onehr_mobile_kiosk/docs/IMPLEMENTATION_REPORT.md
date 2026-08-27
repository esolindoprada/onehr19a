# OneHR Mobile Kiosk — Direct Full Addon Build Report

## Baseline replaced

The latest user workspace contained the stock Odoo tutorial scaffold for
`onehr_mobile_kiosk`: generic manifest, commented controller/model and broad `base.group_user`
CRUD placeholder. It did not implement the OneHR product baseline.

This Direct Full Build replaces that scaffold without inventing a parallel attendance owner.

## Implemented enterprise scope

- exactly `onehr.kiosk.device` and `onehr.kiosk.log`
- Kiosk Operator / Kiosk Administrator separation
- dedicated authenticated service-user binding
- hashed/rotatable/expiring device token
- QR/barcode, NFC and optional geolocation/geofence kiosk UX
- face-ready capability without local biometric storage
- encrypted browser offline queue
- durable queued/processing/synced/failed/blocked/dead-letter server evidence
- bounded exponential retry and scheduled retry
- canonical OneHR Attendance check-in/out bridge
- today's shift snapshot
- soft OneHR Time Off balance + quick request under employee self-service authority
- explicit List/Form/Search for both models
- statusbars, header actions, smart buttons, body actions and One2many row actions
- Log Calendar/Pivot/Graph
- QWeb Kiosk Device Usage report
- 24 tagged runtime test methods
- addon-specific Guardrail and acceptance documentation.

## Deliberate non-ownership

No employee, attendance, leave, branch, biometric, public API/webhook or general integration
canonical model is created. Third-party API/webhook concerns remain `onehr_integrations_api`.

## Codex execution

`CODEX_EXECUTED: NO`

This build was designed and assembled directly. Future Codex use, if explicitly required for a
proven runtime defect, is bounded by the addon Guardrail: maximum two attempts per task and no
repeat of the same root cause beyond one.

## Acceptance status

`SOURCE_ACCEPTANCE: PASS (78 checks, 0 failures)`

`SOURCE_ENTERPRISE_COMPLETENESS: PASS_FOR_RUNTIME`

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

`ONEHR_MOBILE_KIOSK_MOVE_FORWARD_READY: NO`

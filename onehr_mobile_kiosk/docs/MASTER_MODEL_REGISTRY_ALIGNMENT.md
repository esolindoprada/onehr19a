# OneHR Mobile Kiosk — Master Model Registry Alignment

## Product-approved ownership

The OneHR 25 Addons Specification explicitly names the following kiosk data models:

| Model | Ownership | Implementation contract |
|---|---|---|
| `onehr.kiosk.device` | OneHR Mobile Kiosk persistent master | Device registration, service-user binding, token hash/rotation, capabilities, geofence/offline policy and operational KPI |
| `onehr.kiosk.log` | OneHR Mobile Kiosk persistent evidence | Punch/request/heartbeat evidence plus queued/processing/synced/failed/blocked/dead-letter synchronization lifecycle |

The generic scaffold model `onehr_mobile_kiosk.onehr_mobile_kiosk` is not created.

## Canonical models intentionally not duplicated

- `hr.attendance` — owned by Odoo / `onehr_attendance`; this addon only adds a narrow downstream bridge method.
- `hr.employee` — Odoo/Core HR owner; barcode and OneHR employee number are used for identification.
- `hr.work.location` — Odoo/OneHR Base owner; device geofence reads the existing location coordinates.
- `onehr.leave.request`, `onehr.leave.type`, `onehr.leave.allocation` — `onehr_timeoff` owner and soft integration only.
- `onehr.branch` — `onehr_multicompany_branch` owner; no reverse hard dependency.
- external API/webhook credential/log models — `onehr_integrations_api` owner.

## ED classification hard gate

The exact Master Model Registry row/ED labels for `onehr.kiosk.device` and `onehr.kiosk.log`
were not surfaced in the authoritative source material available to this build. The product
specification does prove the model names and ownership, but **ED labels are not invented**.

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

The addon cannot be declared final/frozen until the exact Registry rows are compared. A future
registry comparison may add documentation or compatibility hardening, but Codex may not change
model ownership on its own.

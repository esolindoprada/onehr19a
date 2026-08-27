# OneHR Mobile Kiosk — UI/UX Matrix

| Model / surface | List | Form | Search | Statusbar | Smart buttons | Body actions | One2many row actions | Analysis |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `onehr.kiosk.device` | YES | YES | YES | YES | Activity, Queue, Errors | Open Kiosk, Issue/Rotate Token, Process Queue, Usage Report | Retry, Attendance, Target | KPI fields + PDF |
| `onehr.kiosk.log` | YES | YES | YES | YES | Device, Attendance, HR Target | Retry, Dead Letter, Open Attendance/Target | N/A | Calendar/Pivot/Graph |
| Authenticated kiosk UI | N/A | Kiosk surface | N/A | Connectivity/transaction state | Employee/Schedule/Balance summary | Identify, QR, NFC, Check In, Check Out, Auto, Quick Time Off, Sync Now | Offline encrypted queue | Operational UX |

## Search-view hard gate

Both persistent business models have explicit search views. Search and group-by fields cover
device, employee snapshot, event date/type, synchronization state, geofence, errors and company.

## Enterprise list hard gate

Lists expose decision fields and row actions; they are not name/ID-only scaffolds. Kiosk logs use
decorations for synchronized, failed/dead-letter, blocked and queued/processing conditions.

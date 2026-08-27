# OneHR Mobile Kiosk — Full Structural Inventory

## Persistent business models

1. `onehr.kiosk.device`
2. `onehr.kiosk.log`

Exactly two are created, matching the OneHR product specification.

## Native model extension

- `hr.attendance`
  - `onehr_kiosk_apply_punch(device, kiosk_log)`
  - no new attendance table and no ownership transfer.

## Controllers

Authenticated (`auth="user"`) kiosk routes:

- `GET /onehr/kiosk/<device_code>`
- JSON-RPC `/onehr/kiosk/api/bootstrap`
- JSON-RPC `/onehr/kiosk/api/identify`
- JSON-RPC `/onehr/kiosk/api/punch`
- JSON-RPC `/onehr/kiosk/api/timeoff`
- JSON-RPC `/onehr/kiosk/api/sync`
- JSON-RPC `/onehr/kiosk/api/heartbeat`

Every kiosk JSON-RPC operation requires both normal user authority and the device token.

## Security

- Kiosk Operator
- Kiosk Administrator
- four ACL rows
- global company record rules
- assigned-device operator rules
- company-wide Kiosk Admin rules
- no `base.group_user` ACL
- no business `sudo()`.

## Data / automation

- device sequence `onehr.kiosk.device`
- activity sequence `onehr.kiosk.log`
- five-minute retry cron
- cron discovers due rows as root but rebinds each business sync to the configured service user.

## UI

- Device explicit List/Form/Search
- Log explicit List/Form/Search/Calendar/Pivot/Graph
- statusbars, lifecycle actions, smart buttons, body-form buttons, One2many row actions, chatter
- authenticated kiosk web page
- QR/BarcodeDetector, Web NFC, geolocation, encrypted browser queue, quick Time Off panel
- QWeb Device Usage Summary PDF

## Tests

24 post-install source test methods split across:

- device/token/security
- canonical attendance punch/sync/geofence/privacy
- offline queue/soft integration/evidence lifecycle

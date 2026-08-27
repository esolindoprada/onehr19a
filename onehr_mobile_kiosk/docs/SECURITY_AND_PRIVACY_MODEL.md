# OneHR Mobile Kiosk — Security & Privacy Model

## Two-part device trust

A kiosk request must satisfy both:

1. authenticated Odoo user authority (normally a dedicated Kiosk Operator service user), and
2. the active device's device token.

The raw device token is generated with Python `secrets`, shown once, and persisted only as a
SHA-256 digest plus last four characters. Verification uses constant-time digest comparison.

## Device authorization

- Kiosk Operator: sees/operates only devices assigned to that user.
- Kiosk Administrator: manages devices/tokens/queue for allowed companies.
- Admin implies the accepted Attendance Manager; operator implies accepted Attendance Officer.
- UI invisibility is not security; model methods independently check authority.

## Sensitive data minimization

Server logs do **not** persist:

- raw device token,
- raw QR/NFC credential value,
- employee PIN,
- face image, face template or biometric embedding.

The face-ready flag is capability metadata only.

Offline browser events must retain enough identity/request data to sync later. Those queued
payloads are encrypted with AES-GCM using a WebCrypto key derived from the current device token.
If WebCrypto is unavailable, the UI refuses to store a plaintext offline event.

## Evidence protection

Synchronization result fields, event identity, geolocation, target links, payload hash and errors
cannot be changed through ordinary `write()`. Private server methods perform governed transitions.
Processed logs cannot be deleted through business operations.

## Multi-company

Global company rules always apply. The service-user assignment then narrows Kiosk Operator scope;
Kiosk Admin receives company scope. Employee/device company alignment is validated server-side.

## Elevated execution

Business target operations never call `.sudo()`. The retry cron may be scheduled as `base.user_root`
only to discover due queue rows. Each actual event is immediately re-bound with
`with_user(device.service_user_id)` before Attendance/Time Off business logic executes.

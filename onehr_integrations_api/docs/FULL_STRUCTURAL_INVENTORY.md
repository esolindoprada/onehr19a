# OneHR Integrations API — Full Structural Inventory

## Persistent models

### `onehr.api.key`
Client identity, company, least-privilege service user, scopes, lifecycle, expiry, rate limit,
optional branch boundary, PBKDF2 secret hash/salt/hint, last-use evidence and log smart metrics.
Actions: Generate Credential, Rotate Secret, Activate, Suspend, Revoke, Open Logs.

### `onehr.api.scope`
Stable scope code, risk level, HTTP method/route ownership, company-scope marker and assigned-key
metrics. Actions: Open Keys, Deactivate.

### `onehr.webhook`
Inbound/outbound direction, allow-listed event code, company, target/endpoint, service user,
restricted signing secret, HMAC/rate/retry/timeout policy and last-delivery evidence.
Actions: Rotate Secret, Activate, Pause, Queue Test, Disable, Open Queue/Logs.

### `onehr.api.log`
Immutable request/delivery audit: direction, identity, request ID, scope/event, HTTP metadata,
outcome/status/latency/error, body hashes, optional sanitized body snapshots, archive marker.
Technical creation only; application delete is blocked.

### `onehr.api.queue`
Outbound webhook delivery evidence with dedupe/request identity, payload hash, state, bounded
attempts/backoff, retry timestamp, HTTP/error evidence and delivery logs.
Actions: Process Now, Retry, Dead Letter, Cancel, Open Logs.

## Native transient extension

`res.config.settings`: API enablement, payload/rate/HMAC/CORS settings, log retention, webhook
retry/timeout and explicit HTTP/private-network exceptions.

## Controllers/services

- `controllers/api_v1.py`: explicit v1 routes and stable JSON/error contract.
- `controllers/webhook_inbound.py`: fixed inbound webhook endpoint and allow-listed dispatch.
- `services/runtime.py`: credential, scope, HMAC, replay, rate, company/service-user boundary, redaction/audit.
- `services/domain_adapters.py`: narrow soft adapters; no business `sudo()`.
- `services/webhook_delivery.py`: outbound HMAC, SSRF-safe target validation, no redirects, bounded response/retry.
- `services/openapi.py`: runtime OpenAPI document.

## Security/data/UI

Two custom roles (API Operator, API Administrator), 10 ACL rows, four global company rules,
19 seed scopes, queue sequence, retry/log cron, List/Form/Search for all five models,
Kanban for Webhook/Queue and Pivot/Graph for Log/Queue.

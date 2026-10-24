# OneHR Integrations API — Bounded Runtime Repair Attempt 2

TASK_ID: `ONEHR-INTEGRATIONS-API-DIRECT-FULL-20260831`  
ATTEMPT: `2/2`  
DATE: `2026-08-31`  
TARGET: Odoo 19 Community Edition  
WRITE_SCOPE: `onehr_integrations_api` only  
ROOT_CAUSE_CLASSIFICATION: `ADDON_SOURCE_FAILURE`

## First concrete runtime failure

Activation failed while validating `views/webhook_views.xml`, XML ID
`view_onehr_webhook_search`. Odoo reported:

`Unsearchable field "failed_count" in path "failed_count"`

The `Has Dead Letters` filter correctly represented an enterprise operational need, but
its domain referenced `failed_count`, which was a non-stored computed Integer without a
custom search method. The view was therefore invalid.

## Correction

The approved feature is preserved rather than deleted:

- `onehr.webhook.failed_count` remains a computed Dead Letter metric;
- the field is now `store=True`;
- its existing dependency on `queue_ids.state` remains, so queue lifecycle changes
  recompute the stored count;
- the `Has Dead Letters` search filter remains unchanged;
- runtime regression test 26 verifies the field is searchable;
- source acceptance verifies both searchability and filter preservation.

No sibling addon, dependency, canonical model, ACL, record rule, API route, webhook
transport, retry policy, or audit behavior changed.

## Release

Previous version: `19.0.1.0.0`  
Repair version: `19.0.1.0.1`

## Retry hard gate

This consumes Attempt 2/2 for the current Integrations API build task. If activation of
this exact package fails again, the task must STOP with:

`STOP_REASON: MAX_ATTEMPTS_REACHED`

A new source mutation requires an explicit new bounded repair task after classification.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`  
`ONEHR_INTEGRATIONS_API_MOVE_FORWARD_READY: NO`

# OneHR Integrations API — Bounded Runtime Repair Evidence

TASK_ID: ONEHR-INTEGRATIONS-API-DIRECT-FULL-20260831  
TARGET_ADDON: onehr_integrations_api  
ATTEMPT: 2 of 2  
DATE: 2026-08-31  
TARGET_PLATFORM: Odoo 19 Community Edition  
SOURCE_WRITE_SCOPE: onehr_integrations_api only  
INPUT_BASELINE: latest user-supplied OneHR workspace plus first complete Windows activation traceback  
ROOT_GUARDRAIL_SHA256: 9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55  
ROOT_CAUSE_CLASSIFICATION: ADDON_SOURCE_FAILURE

## Runtime evidence

Odoo stopped while validating `views/webhook_views.xml` / `view_onehr_webhook_search`:

`Unsearchable field "failed_count" in path "failed_count"`

The approved `Has Dead Letters` search filter used:

`[("failed_count", ">", 0)]`

while `onehr.webhook.failed_count` was declared as a non-stored compute without a
custom search method. The view therefore referenced a field Odoo could not use in a domain.

## Bounded correction

- preserve the `Has Dead Letters` search feature;
- preserve the approved `onehr.webhook` model;
- change only `failed_count` to a stored computed metric (`store=True`);
- retain dependency on `queue_ids.state` so Dead Letter transitions recompute the metric;
- add runtime regression test `test_26_webhook_dead_letter_count_is_searchable`;
- add source-acceptance regression gates for field searchability and filter preservation;
- bump addon version from `19.0.1.0.0` to `19.0.1.0.1`.

No model, field, API endpoint, webhook contract, role, ACL, record rule, dependency,
queue lifecycle, audit evidence, or enterprise UI capability was deleted or weakened.
No sibling addon was edited.

## Retry hard gate

This is Attempt 2/2 for `ONEHR-INTEGRATIONS-API-DIRECT-FULL-20260831`. If this exact
package produces another activation failure, do not perform an automatic third source
mutation. Capture the first complete traceback and stop under the root Guardrail.

`ONEHR_INTEGRATIONS_API_MOVE_FORWARD_READY: NO`

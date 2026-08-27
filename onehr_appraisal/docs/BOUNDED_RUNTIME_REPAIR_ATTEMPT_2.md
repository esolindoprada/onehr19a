# OneHR Appraisal — Bounded Runtime Repair Evidence

TASK: `onehr_appraisal` activation repair  
ATTEMPT: 2 of 2  
DATE: 2026-08-21  
TARGET_PLATFORM: Odoo 19 Community Edition  
SOURCE_WRITE_SCOPE: `onehr_appraisal` only  
ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`

## Runtime evidence

Activation failed while Python imported `models/cycle.py`.

Observed Odoo 19 exception:

`NotImplementedError: Compute method cannot depend on field 'id'.`

The failing source dependency was:

`@api.depends("template_score_ids.id", ...)`

Odoo 19 explicitly rejects a compute dependency path whose terminal field is `id`.

## Bounded correction

Only the dependency declaration is corrected:

- removed `template_score_ids.id`;
- added `template_score_ids`;
- added `template_score_ids.parent_score_id`.

This preserves the original metric behavior:
- recompute when template-score membership changes;
- recompute when a score line changes between root target and child feedback.

No model, field, workflow, security role, record rule, UI capability, integration
contract, hard dependency, or ownership boundary was removed or moved.

## Prevention

`tools/source_acceptance.py` now rejects every `@api.depends()` string equal to `id`
or ending in `.id`, so this Odoo 19 compatibility defect cannot silently pass the
same source gate again.

## Release marker

Previous source version: `19.0.1.0.0`  
Repair version: `19.0.1.0.1`

## Retry hard gate

This is bounded repair Attempt 2/2 for the current Appraisal build task.

If another activation failure occurs after deploying this exact package, do not
perform an automatic third source repair. Capture the first complete traceback and
classify it under the OneHR root Guardrail.

`ONEHR_APPRAISAL_MOVE_FORWARD_READY: NO`

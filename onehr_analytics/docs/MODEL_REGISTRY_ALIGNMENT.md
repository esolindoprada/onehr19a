# OneHR Analytics — Model Registry Alignment

The supplied Analytics product contract explicitly names:
- `onehr.analytics.tile`
- `onehr.kpi.snapshot`
- `onehr.mixin.analytics`

This build implements exactly those names: two persistent models plus one abstract mixin.

`REGISTRY_MODEL_NAME_ALIGNMENT_SOURCE: PASS_TO_PRODUCT_BASELINE`

The accessible workspace does not expose authoritative Master Model Registry ED0–ED5 rows for
these Analytics entries. No ED class is invented.

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

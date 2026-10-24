# OneHR Integrations API — Model Registry Alignment

The supplied product contract explicitly identifies these persistent models:
`onehr.api.key`, `onehr.api.scope`, `onehr.webhook`, `onehr.api.log`, `onehr.api.queue`.
This build implements exactly those five and extends native transient `res.config.settings`.

The latest workspace does not expose authoritative Master Model Registry ED0–ED5 rows for these
five models. ED classifications are therefore not invented.

REGISTRY_MODEL_NAME_ALIGNMENT_SOURCE: PASS_TO_PRODUCT_BASELINE  
REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION

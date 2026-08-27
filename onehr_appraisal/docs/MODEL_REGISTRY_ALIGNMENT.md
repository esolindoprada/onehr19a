# OneHR Appraisal — Model Registry Alignment

The OneHR 25-addons Appraisal product contract identifies exactly these core models:

- `onehr.appraisal.cycle`
- `onehr.appraisal.form`
- `onehr.appraisal.score`

This build implements exactly those three persistent Appraisal business models.

`REGISTRY_MODEL_NAME_ALIGNMENT_SOURCE: PASS_TO_PRODUCT_BASELINE`

The supplied Appraisal scaffold/workspace evidence does not expose authoritative Master
Model Registry ED classification rows for these three models. ED labels are not invented.

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

Canonical worker ownership remains native `hr.employee`; no `onehr.employee` is created.

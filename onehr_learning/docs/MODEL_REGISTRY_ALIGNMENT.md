# OneHR Learning — Model Registry Alignment

The OneHR 25-addons product baseline explicitly names these eight Learning models:

- onehr.learning.course
- onehr.learning.session
- onehr.learning.enrollment
- onehr.learning.attendance
- onehr.learning.certificate
- onehr.learning.vendor
- onehr.learning.budget
- onehr.learning.cost.line

This source implements exactly those eight persistent Learning business models and rejects
the generic tutorial placeholder.

`REGISTRY_MODEL_NAME_ALIGNMENT_SOURCE: PASS_TO_PRODUCT_BASELINE`

The exact ED0/ED1/ED2/ED3/ED4 labels from the authoritative Master Model Registry v1 were
not exposed in the supplied Learning scaffold/source excerpt. They are deliberately not
invented.

`REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION`

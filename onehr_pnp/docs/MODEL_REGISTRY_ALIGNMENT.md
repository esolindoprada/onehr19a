# OneHR PnP — Model Registry Alignment

The supplied PnP product contract explicitly identifies:
- `onehr.policy`
- `onehr.policy.ack`
- `onehr.policy.evidence`
- `res.config.settings` extension

This Direct Full build creates exactly the three persistent PnP models and
extends the approved transient Settings model.

Ownership remains upstream for:
- workforce masters: Odoo HR / CoreHR;
- approval engine: OneHR Workflow Approval;
- immutable document archive: OneHR Document;
- operational SOP: OneHR SOP;
- Portal/Analytics/API/Branch: downstream optional owners.

The accessible workspace does not expose authoritative Master Model Registry
ED0–ED5 rows for the three PnP persistent models. No ED classification is invented.

REGISTRY_MODEL_NAME_ALIGNMENT_SOURCE: PASS_TO_SUPPLIED_PRODUCT_BASELINE  
REGISTRY_ED_CLASSIFICATION: PENDING_EXACT_REGISTRY_ROW_VERIFICATION

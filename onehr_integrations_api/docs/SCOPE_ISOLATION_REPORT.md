# OneHR Integrations API — Scope Isolation Report

TASK: `ONEHR-INTEGRATIONS-API-DIRECT-FULL-20260831`  
ATTEMPT: 2/2  
LATEST_WORKSPACE_REFERENCE: `onehr19a(20260831-113555).md` uploaded `2026-08-31T11:35:52Z`  
LATEST_WORKSPACE_SHA256: `NOT_AVAILABLE_FROM_FILE_REFERENCE`  
ROOT_GUARDRAIL_SHA256: `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`

Source write scope is exactly `onehr_integrations_api`. Sibling OneHR content was inspected only to
consume existing model-service contracts and ownership boundaries. No sibling addon source is
included or modified by this deliverable.

The source hash of the uploaded workspace itself is deliberately not invented because the current
file reference exposes searchable content/metadata rather than raw local bytes. The authoritative
root Guardrail checksum is available in the workspace and is preserved above.

`SCOPE_ISOLATION_RESULT: PASS_PACKAGE_SCOPE`


## Attempt-2 bounded changes

Runtime/business source changed only where required by the proven defect:

- `__manifest__.py` — version `19.0.1.0.1`;
- `models/webhook.py` — `failed_count` stored/searchable;
- `tests/test_webhook_queue_and_contracts.py` — regression test 26;
- `tools/source_acceptance.py` — regression gate and expected version/test count;
- evidence/documentation and regenerated fingerprints/reports inside this addon only.

No sibling OneHR addon is included or modified.

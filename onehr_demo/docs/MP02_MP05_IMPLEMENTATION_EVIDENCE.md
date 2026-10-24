
# OneHR Demo — MASTER PROMPT 05 Implementation Evidence

TASK_ID: `ONEHR-DEMO-MP05-DIRECT-FULL-20260910`

```text
MASTER_PROMPT_ID: 05
PHASE_TITLE: Enterprise Company, Branch/Site & Organizational Foundation
TARGET_ADDON: onehr_demo
WRITE_SCOPE: onehr_demo/**
ATTEMPT: 1
AUTHORITATIVE_SOURCE_LABEL: onehr19a(20260910-065304).md
AUTHORITATIVE_SOURCE_SHA256: db960a2dfb849420144d82a00bbd35a030f0618da5d6d67dfb4135fea62e0e8e
ROOT_GUARDRAIL_SHA256: 9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55
PREREQUISITE_PHASES: MP00-MP04
ROOT_CAUSE_CLASSIFICATION: N/A — APPROVED_NEXT_PHASE_IMPLEMENTATION
MODELS_TOUCHED: onehr.demo.* control plane only
PRODUCTION_MODELS_CALLED: res.company, onehr.branch, hr.department
SECURITY_TOUCHED: NONE
SIDE_EFFECT_CLASSIFICATION: SAFE_INTERNAL
RESET_POLICY_TOUCHED: REUSE_ON_REBUILD
STATIC_RESULT: PASS — 1034 PASS / 0 FAIL
RUNTIME_RESULT: NOT_RUN
IDEMPOTENCY_RESULT: STATIC_CONTRACT_PRESENT / RUNTIME_NOT_RUN
RESET_RESULT: STATIC_CONTRACT_PRESENT / RUNTIME_NOT_RUN
SECURITY_RESULT: NO_ACL_WEAKENING / RUNTIME_NOT_RUN
ANALYTICS_TRACEABILITY_RESULT: N/A_FOR_MP05
FIRST_ACTIONABLE_ROOT_CAUSE: N/A
STOP_REASON: N/A
PHASE_MOVE_FORWARD_READY: NO — WINDOWS RUNTIME EVIDENCE REQUIRED
```

## Implementation boundary

MP05 reuses the scenario's selected `res.company`, creates deterministic
`onehr.branch` masters and canonical `hr.department` organization units, registers
every logical entity in `onehr.demo.reference`, validates company/hierarchy/effective
date integrity, and supports provenance-only reset/rebuild.

No production sequence is consumed. No sibling addon is edited. No broad `sudo()` is
added. No production ACL/record rule is weakened.

## Runtime gate

A source/static PASS only authorizes the user's native Windows trial. MP05 becomes
PASS/frozen only after:

- addon upgrade PASS;
- Refresh Source Compatibility PASS;
- Validate Readiness PASS;
- QUICK generation PASS;
- second QUICK generation creates zero duplicates;
- Validate Dataset PASS;
- Reset Preview has zero unhandled MP05 references;
- Execute Safe Reset PASS;
- Rebuild PASS with the same retained target IDs.


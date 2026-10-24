
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

## Full-path deterministic closure added before runtime trial

The final source pass also closes non-reactive failure classes that would otherwise
surface only after repeated native trials:

- deterministic code collision searches include archived (`active_test=False`) masters;
- scenario identity (`code`, company, profile, versions, reference clock, timezone,
  locale/country and seed) becomes immutable once business provenance exists;
- compatibility fingerprint excludes database/operator/timestamp/source-label metadata;
- reset is one savepoint-bounded atomic operation with an explicit active-provenance
  postcondition;
- MP05 regression suite includes the implemented registry contract, scenario identity
  freeze and archived deterministic collision behavior;
- canonical branch audit/chatter evidence is explicitly classified as protected
  production-side evidence and is never deleted by demo reset.

The original MP05 package reached `1022 PASS / 2 expected runtime warnings / 0 FAIL`.
After the 19.0.1.0.2 navigation closure and expanded operator-surface gates, current static acceptance is:

`1034 PASS / 2 expected runtime warnings / 0 FAIL`.

The latest supplied composite is `onehr19a(20260910-065304).md` with SHA-256
`db960a2dfb849420144d82a00bbd35a030f0618da5d6d67dfb4135fea62e0e8e`.
A complete file-level diff against the prior authority shows that all changes are confined to `onehr_demo`; the 25 production sibling addons are unchanged.

## 19.0.1.0.2 operator-navigation closure

The latest supplied composite is `onehr19a(20260910-065304).md` (`db960a2dfb849420144d82a00bbd35a030f0618da5d6d67dfb4135fea62e0e8e`). A full composite diff against the prior MP05 authority found **no production-addon changes outside `onehr_demo`**. The observed inability to create a Demo Dataset is classified `ADDON_SOURCE_FAILURE` inside the `onehr_demo` navigation layer: the Scenario action was attached to a parent menu that also owned children. Version 19.0.1.0.2 exposes a dedicated **Demo Control Center** leaf and adds static/runtime regression gates. No generator/business/reset/security semantics are redesigned.



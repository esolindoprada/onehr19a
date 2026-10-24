
# OneHR Demo — Project Identity Preflight

TASK_ID: `ONEHR-DEMO-MP05-DIRECT-FULL-20260910`  
TARGET_ADDON: `onehr_demo`  
VERSION: `19.0.1.0.4`  
PLATFORM: Odoo 19 Community Edition  
WRITE_SCOPE: `onehr_demo/**` only  
ATTEMPT: `1 / 2`

## Authority

- Latest composite source: `onehr19a(20260910-065304).md`
- Composite SHA-256: `db960a2dfb849420144d82a00bbd35a030f0618da5d6d67dfb4135fea62e0e8e`
- Governing Master Prompt V2 SHA-256: `21da5974ff755c03ffb2cc12d0e073832370c3e4dcefc3af21376e5b3dc52457`
- Oracle HRMS benchmark SHA-256: `a02355585ce8a5a33427e3ac5a7ef424618986a778b906b165606a178a5ceb98`
- Root Guardrail SHA-256: `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`

The authoritative production topology remains 25 OneHR addons. This task does not
change sibling-addon ownership or dependency topology.

## Current move

MP02–MP04 control-plane architecture is preserved. MP05 implements exactly
`foundation.enterprise`; MP06–MP24 remain planned but their complete production
contracts remain compatibility-audited.

The latest source baseline includes the already-repaired production versions:

- `onehr_multicompany_branch 19.0.1.0.2`
- `onehr_career_succession 19.0.1.0.1`
- `onehr_pnp 19.0.1.0.1`

Therefore the previous MP02–MP04 compatibility lock is intentionally stale and must
be refreshed after this addon upgrade.

`ROOT_CAUSE_CLASSIFICATION: N/A — APPROVED_NEXT_PHASE_IMPLEMENTATION`  
`SIBLING_SOURCE_MUTATION: NONE`

## 19.0.1.0.2 bounded runtime repair classification

`ROOT_CAUSE_CLASSIFICATION: ADDON_SOURCE_FAILURE`

The control-plane Scenario model/action/ACL was valid, but the operator navigation contract was incomplete: the Scenario action was attached to a parent menu that also owned child menus. This repair changes only `onehr_demo` navigation/evidence metadata and regression gates.


## 19.0.1.0.4 bounded deterministic-sequence closure

`onehr_demo` no longer treats mutable production `ir.sequence` rows/counters as a generation prerequisite. All 34 production sequence policies remain frozen and audited, direct demo sequence consumption remains forbidden, and the compatibility fingerprint excludes mutable sequence availability. No production sibling addon is modified.


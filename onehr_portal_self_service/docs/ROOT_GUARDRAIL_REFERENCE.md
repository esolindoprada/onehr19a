
# OneHR Root Guardrail Reference

ROOT_GUARDRAIL_ID: ONEHR-EDG-V1
ROOT_GUARDRAIL_STATUS: APPROVED_HARD_GATE
ROOT_GUARDRAIL_SHA256: 9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55

This addon-specific Guardrail supplements and never overrides the authoritative OneHR root
Enterprise Development Guardrail. Where the current user-approved Hard Gate list is stricter,
including explicit HARD GATE 11 Database Identifier & ORM Naming Safety, this addon enforces
that stricter requirement without changing sibling architecture.

Codex remains a bounded implementation worker with no architecture, simplification,
deletion, ownership or dependency-change authority and a maximum of two bounded attempts.


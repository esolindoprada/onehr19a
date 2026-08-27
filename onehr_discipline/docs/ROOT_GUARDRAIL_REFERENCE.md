# OneHR Root Guardrail Reference

ROOT_GUARDRAIL_ID: ONEHR-EDG-V1  
ROOT_STATUS: APPROVED_HARD_GATE  
ROOT_SHA256: 9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55

This Discipline-specific Guardrail supplements and never relaxes the root OneHR Guardrail.

Codex remains BOUNDED_IMPLEMENTATION_WORKER:
- architecture authority: none
- simplification authority: none
- deletion authority: none
- model ownership change authority: none
- dependency change authority: none
- maximum bounded repair attempts: 2
- same root cause repeated at most once
- static/runtime PASS is not enterprise completeness
- move-forward requires every applicable hard gate

The user-specified Discipline work additionally defines HARD GATE 11 explicitly
as Database Identifier & ORM Naming Safety.

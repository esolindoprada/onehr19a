
# OneHR Root Guardrail Reference

ROOT_GUARDRAIL_ID: ONEHR-EDG-V1  
ROOT_STATUS: APPROVED_HARD_GATE  
ROOT_SHA256: 9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55

This addon-specific Guardrail supplements and never overrides the root OneHR Guardrail.

Codex remains `BOUNDED_IMPLEMENTATION_WORKER`:
- architecture authority: none
- simplification authority: none
- deletion authority: none
- model ownership change authority: none
- dependency change authority: none
- max attempts per bounded repair task: 2
- max same-root-cause repeat: 1
- static/runtime PASS is not enterprise completeness
- move-forward requires every applicable hard gate


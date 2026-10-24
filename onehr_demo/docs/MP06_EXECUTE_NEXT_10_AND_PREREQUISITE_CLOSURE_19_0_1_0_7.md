# OneHR Demo 19.0.1.0.7 — MP06 / Execute Next 10 Closure

## Runtime defect closed

The previous bounded release could reach `organization.jobs_positions` with a QUICK scenario whose MP05 foundation had no provenance for `onehr_demo.enterprise.organization.department.it`. The cause was a profile-rank mismatch: the rank-1 `it_manager` consumer required `it`, while the MP05 `it` department was rank 2.

## Corrected contract

- `it` department rank: 1
- `learning` department rank: 2
- `data` department rank: 2
- `procurement` remains rank 3
- QUICK department shape: 7
- STANDARD department shape: 12
- FULL ENTERPRISE department shape: 16

MP06 uses the same deterministic MP05 department producer to reconcile missing profile departments before consumption. No production sequence, broad cleanup, `sudo()`, or generic unlink is used. Every reconciled department receives `foundation.enterprise` provenance.

## Execute Next 10

`action_execute_next_10()` executes at most 10 contracts from the frozen `(phase, key)` order. It stops immediately on the first runtime failure or unimplemented contract. A failure leaves the failed checkpoint and run evidence persisted and returns a sticky danger notification with `reload_form=False`, specifically so the operator can copy the exact message.

## Acceptance

This is a source/static corrected release. Windows/Odoo runtime acceptance must still be performed on the user's Odoo 19 environment.

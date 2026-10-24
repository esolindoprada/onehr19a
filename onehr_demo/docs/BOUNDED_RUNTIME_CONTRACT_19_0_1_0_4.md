
# OneHR Demo 19.0.1.0.4 — Bounded Runtime Contract

## Objective
Close the hidden dependency between demo generation and mutable production sequence state without redesigning any production addon.

## Contract
1. `onehr_demo` never calls `ir.sequence.next_by_code()`.
2. Each frozen production sequence policy explicitly declares `demo_generation_dependency=NONE` for the current implemented demo path.
3. Compatibility still audits all 34 sequence policies as evidence.
4. Sequence row existence and current counters are non-blocking.
5. Sequence runtime state is excluded from the compatibility fingerprint.
6. Deterministic demo identity is scenario/domain/entity/stable-key + provenance.
7. Reset/rebuild resolves retained targets from provenance, not sequence counters.
8. No sibling production addon source is changed.

## Acceptance
`MP05_MOVE_FORWARD_READY` remains a separate Windows runtime decision. This package is source/static corrected and ZIP-ready; runtime installation/generation must be performed on the user's Odoo 19 Windows environment.


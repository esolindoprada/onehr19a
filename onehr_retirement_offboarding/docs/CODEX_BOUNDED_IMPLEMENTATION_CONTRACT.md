# Codex Bounded Implementation Contract

Codex role: `BOUNDED_IMPLEMENTATION_WORKER`.

Allowed after a runtime defect is proven: inspect the exact first failure, classify it, make the smallest target-local architecture-preserving repair, add regression evidence, and stop.

Forbidden: architecture redesign, simplification, deletion, model ownership movement, dependency redesign, security weakening, sibling edits, test suppression, or retry loops.

`MAX_CODEX_ATTEMPTS_PER_TASK: 2`  
`MAX_REPEAT_OF_SAME_ROOT_CAUSE: 1`

Current Direct Full Build occupies Attempt 1. If a distinct target-local source defect is proven at runtime, only Attempt 2 remains. If Attempt 2 fails: `STOP_REASON: MAX_ATTEMPTS_REACHED`.

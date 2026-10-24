# OneHR Analytics — Codex Bounded Implementation Contract

Codex is an implementation worker only.

- Architect: NO
- Simplifier: NO
- Deletion authority: NO
- Model ownership authority: NO
- Dependency topology authority: NO
- Automatic retry engine: NO
- Maximum attempts for one proven source task: 2
- Maximum repeat of the same root cause: 1

For runtime work, capture the first concrete failure, classify it, and mutate only if it proves
a target-local source/version-compatibility defect. Do not respond to an environment/harness
failure by changing business source. Attempt 2 must include a regression gate. A failed second
attempt terminates source mutation with `STOP_REASON: MAX_ATTEMPTS_REACHED`.

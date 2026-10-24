
# OneHR Demo — Deterministic Production Sequence Policy

## Hard rule

`onehr_demo` MUST NOT call `ir.sequence.next_by_code()` directly.

Every production sequence discovered in the frozen OneHR source has an explicit policy in
`services/contracts.py`. Every policy declares:

- `direct_demo_next_by_code = FORBIDDEN`;
- `demo_generation_dependency = NONE` for the currently implemented demo generators.

## Critical bounded change in 19.0.1.0.3

Production `ir.sequence` rows and mutable counters are **audit-only** for the current
`onehr_demo` generation path. Their presence, current `number_next`, or current counter
position MUST NOT determine whether MP05 can generate, reset, rebuild, or resume.

The compatibility audit still reports every frozen sequence policy and its stable identity
contract so the complete production path remains visible. However:

- missing sequence configuration does not block current demo generation;
- mutable sequence counters are not part of compatibility truth;
- sequence availability is excluded from the compatibility fingerprint;
- deterministic demo identity comes from scenario + domain + entity + stable key;
- production sequence values may be used by production business logic as presentation numbers,
  but `onehr_demo` never consumes them to establish identity.

## MP05

MP05 consumes **zero** production sequences. Branch code and department `onehr_code` are
derived with `stable_identifier()` from the scenario code plus fixed catalog tokens.
Provenance uses:

`<scenario>.<domain>.<entity>.<stable-key>`

Therefore repeated generation, reset/rebuild, and resume do not depend on mutable database
sequence counters.


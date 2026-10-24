
# Deterministic Model Order Policy

The demo execution controller orders frozen generator contracts by:

```text
(phase, generator_key)
```

The following are explicitly **not** authoritative for demo ordering:

- `ir.sequence` next numbers;
- production sequence counters;
- mutable production transaction order;
- browser/run creation order;
- last run ID;
- database insertion order.

A generator is complete only when a retained scenario-wide checkpoint for that generator is `PASS`.
The controller then selects the first contract in frozen order without a PASS checkpoint.


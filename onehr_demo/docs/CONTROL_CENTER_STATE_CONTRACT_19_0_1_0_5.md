
# Full Control-Center State Contract 19.0.1.0.5

The Control Center has two independent concerns:

1. lifecycle state (`compatibility`, `readiness`, generation, validation, reset);
2. model-by-model execution progress.

`generation_enabled=True` intentionally renders **Disable Demo Generation**. This is the expected state after the safety gate has been enabled; the Enable button is hidden to prevent duplicate enablement.

Model-by-model progress is computed from retained PASS checkpoints across the whole scenario. It is never inferred from the last run ID or a mutable production sequence.


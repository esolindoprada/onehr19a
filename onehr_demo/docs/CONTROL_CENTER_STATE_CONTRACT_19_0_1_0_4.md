
# OneHR Demo 19.0.1.0.4 — Full Control-Center State Contract Closure

## Root cause closed
The server correctly persisted `state=ready` and `readiness_status=ready`, but lifecycle actions returned only `display_notification`. Odoo therefore kept the previously loaded form record in the browser, leaving the statusbar and state-driven buttons stale.

## Contract correction
Every lifecycle-changing Control Center notification can request a client-side form reload through `params.next = {type: ir.actions.client, tag: reload}`. The server remains the authority; the reload only synchronizes the rendered form with committed state.

Covered lifecycle actions:
- Source Compatibility PASS/FAIL
- Demo Generation enable/disable
- Readiness PASS/BLOCKED
- Generation PASS/FAILED
- Dataset Validation PASS/FAILED
- Reset Preview
- Safe Reset PASS/FAILED

## Failure persistence correction
Generation and dataset-validation failures no longer re-raise after recording the bounded failure state. The action returns a failure notification, allowing the transaction containing the run/checkpoint evidence and `paused_failed` state to commit. Safe Reset failures likewise return to `reset_previewed` with failed run evidence.

## Deterministic operator flow
`Compatible → Ready → Generating → Generated → Validating → Validated → Reset Previewed → Resetting → Reset → Ready → Generating`

Button visibility is still state-driven and server actions remain independently guarded. UI refresh is not treated as authorization.


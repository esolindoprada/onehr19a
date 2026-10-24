
# OneHR Demo — Windows Runtime Acceptance for 19.0.1.0.4

Target: user's Odoo 19 Community Edition Windows OneHR database.

## Deployment

1. Replace the complete `onehr_demo` folder with version `19.0.1.0.4`.
2. Restart Odoo.
3. Update Apps List.
4. Upgrade **OneHR Enterprise Demo Dataset**.
5. Confirm no pending module operation remains.

## Full-path preflight

Open the scenario and run **Refresh Source Compatibility**.

Expected baseline includes 25 production OneHR addons and the latest repaired versions
of Branch, Career/Succession and P&P. The audit must PASS all current required production contracts. All 34 sequence policies
remain visible in Compatibility Evidence, but mutable production sequence rows/counters are
not a prerequisite for MP05 readiness or generation.

## MP05 acceptance sequence

Use QUICK first:

1. NON-PRODUCTION acknowledgement checked.
2. Enable Demo Generation.
3. Validate Readiness → PASS.
4. Generate Quick Dataset → PASS.
5. Check latest generation run: one `foundation.enterprise` checkpoint PASS.
6. Run Generate Quick again → created count must be `0`; targets must be reused.
7. Validate Dataset → Structural PASS.
8. Reset Preview → every MP05 row must show `RETAIN_FOR_REBUILD`; zero missing handlers.
9. Execute Safe Reset → active MP05 provenance becomes invalidated; business masters remain. Canonical branch audit/chatter evidence remains intentionally protected.
10. Rebuild Dataset → readiness is rechecked; the exact retained target IDs are reused.

## Expected QUICK shape

- selected legal company: 1 reused;
- branches: 2;
- organization units: 6;
- active MP05 references after generation/rebuild: 9.

## Failure handling

Capture the complete Compatibility Evidence / checkpoint/log from one run. Do not
patch the first traceback line in isolation. A source mutation is permitted only if
evidence proves a distinct target-local defect and the bounded retry contract allows it.

`WINDOWS_RUNTIME_ACCEPTANCE: NOT_RUN`
`MP05_MOVE_FORWARD_READY: NO`

## Operator navigation regression

After upgrade, open **OneHR → Configuration → Enterprise Demo Dataset → Demo Control Center**. The Scenario list must expose **New** for a Demo Administrator. Create/open a scenario there. The five **Demo Evidence** menu actions remain non-creation evidence surfaces by design.


# OneHR Analytics — Windows Runtime Acceptance

Target runtime: Odoo 19 Community Edition on the user's Windows OneHR instance.

## Installation gate
1. Replace the complete existing `onehr_analytics` folder; do not merge the tutorial scaffold.
2. Stop/restart Odoo so Python imports are cold.
3. Update Apps List.
4. Install `OneHR Analytics & KPI Dashboards`.
5. Capture the **first complete traceback** if installation fails.

## Runtime checks after successful install
- Registry contains exactly the two persistent Analytics models plus abstract mixin.
- Analyst/Manager/Admin roles load under Odoo 19 privilege architecture.
- Global company rules isolate Tile and Snapshot.
- Dashboard, Tile Configuration and KPI Trend & Evidence menus open.
- Tile List/Form/Search/Kanban validate and render.
- Snapshot List/Form/Search/Pivot/Graph validate and render.
- Manual tile can activate and generate one immutable snapshot.
- Re-generating the same tile/period does not duplicate evidence.
- Analyst can favorite only self and cannot configure KPI definition.
- Manager can test/generate providers but does not gain source-domain authority.
- Snapshot source drill-through obeys source ACL/rules.
- Threshold warning/critical state and activities work.
- Daily/weekly/monthly cron generation advances next date without infinite retry.
- Retention cron archives old evidence and never deletes it.
- Appraisal/Learning/Career service tiles work only for users authorized by those addons.
- Branch-scoped KPI fails closed when source branch ownership cannot be verified.
- CSV export downloads a deterministic aggregate-only dataset.

## Bounded repair rule
This direct-full build is Attempt 1/2. If the first runtime failure is a proven target-local
source or Odoo-version-compatibility defect, one bounded Attempt 2/2 is available. Environment
or deployment failures do not authorize source mutation. If Attempt 2 fails, STOP with
`STOP_REASON: MAX_ATTEMPTS_REACHED`.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING`
`ONEHR_ANALYTICS_MOVE_FORWARD_READY: NO`

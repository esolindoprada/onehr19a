# OneHR Analytics & KPI Dashboards

Enterprise analytics for OneHR NEW on Odoo 19 Community Edition.

This Direct Full Addon Build replaces the supplied tutorial scaffold. The approved
model footprint is intentionally small and ownership-safe:

- persistent `onehr.analytics.tile` — governed KPI definition, thresholds, scheduling,
  favorites, cached latest result and drill-through configuration;
- persistent `onehr.kpi.snapshot` — immutable periodic KPI evidence and trend history;
- abstract `onehr.mixin.analytics` — shared period, threshold, domain and formatting helpers.

Hard dependency is exactly `onehr_security`. Business-domain addons remain soft
providers. Analytics consumes source data/services; it does not become the owner of
employees, applicants, attendance, leave, payroll, learning, appraisal, talent or
case transactions.

Main workflow: **Draft → Active → Paused → Active → Retired**. Active tiles can create
idempotent daily/weekly/monthly snapshots. Warning/critical snapshots can create
mail activities for configured recipients without inventing a separate alert table.

Replace the complete old `onehr_analytics` folder; do not merge tutorial files.
Restart Odoo, Update Apps List, then install **OneHR Analytics & KPI Dashboards**.

Run `python tools/source_acceptance.py` before runtime deployment. Source acceptance
is not runtime acceptance; use `docs/WINDOWS_RUNTIME_ACCEPTANCE.md` for the real server.

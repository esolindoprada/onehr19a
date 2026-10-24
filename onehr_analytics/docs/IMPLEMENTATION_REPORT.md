# OneHR Analytics — Direct Full Implementation Report

TASK: `ONEHR-ANALYTICS-DIRECT-FULL-20260831`  
ATTEMPT: `1 / 2`  
VERSION: `19.0.1.0.0`  
WRITE_SCOPE: `onehr_analytics` only  
BASELINE_CLASSIFICATION: `ADDON_SOURCE_FAILURE`

## What changed
The generic tutorial scaffold was replaced by an enterprise Analytics layer with exactly two
persistent models and one abstract mixin. The addon now provides KPI definition lifecycle,
manual/aggregate/service providers, immutable periodic evidence, target/threshold evaluation,
alert activities, previous/MoM/HoH/YoY trend evidence, source drill-through, favorites, CSV
export, scheduled generation and retention archival.

## Architecture decisions already implied by supplied product contract
- KPI tiles and snapshots are Analytics-owned.
- Transaction models remain owned by their source addons.
- Optional bridges are soft-coupled.
- Integration API remains external transport owner.
- Branch remains branch-master owner.
- No arbitrary formula execution is introduced.

## Professional UI
Tile receives a native CE executive Kanban plus List/Form/Search. The form includes lifecycle
Action Buttons, Statusbar, Snapshot/Breach Smart Buttons, body actions, and One2many evidence
row navigation. Snapshot gets immutable Form, List/Search and Pivot/Graph analysis.

## Community Edition discipline
The old product marketing mentioned Spreadsheet/Cohort. This build does not pretend those
Enterprise-only/non-native capabilities exist. It uses supported Odoo 19 CE surfaces and CSV
export for external BI interchange.

## Runtime claim
Source acceptance completed with 226 PASS, 2 documented non-blocking warnings and 0 FAIL.
No Windows/Odoo runtime PASS is claimed by source validation. Runtime acceptance remains
separate and pending.

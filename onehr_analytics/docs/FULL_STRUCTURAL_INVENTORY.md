# OneHR Analytics — Full Structural Inventory

## Persistent business/evidence models
1. `onehr.analytics.tile` — KPI definition, provider configuration, lifecycle, target,
   thresholds, schedule, favorites, cached executive state and snapshot orchestration.
2. `onehr.kpi.snapshot` — immutable periodic KPI evidence, threshold outcome, trends,
   sanitized provider provenance and drill-through metadata.

## Abstract model
3. `onehr.mixin.analytics` — period, trend, domain parsing, threshold and JSON helpers.

## Provider service
`models/provider_engine.py` is a plain bounded service object, not an ORM model. It supports
only Manual Value, Approved Model Aggregate and three explicit OneHR KPI service families.

## Security
- Analytics Analyst
- Analytics Manager
- Analytics Administrator
- two global company rules
- six ACL rows

## Scheduled jobs
- due KPI snapshot generation
- snapshot evidence archival by configured retention horizon

Archival never deletes snapshot evidence.

## UI inventory
### `onehr.analytics.tile`
- List
- Form
- Search
- Kanban executive dashboard
- lifecycle header buttons and statusbar
- snapshot/breach smart buttons
- body buttons for favorite, provider test, drill-through and CSV export
- One2many snapshot evidence with row actions
- chatter/activity

### `onehr.kpi.snapshot`
- List
- Form (read-only evidence)
- Search
- Pivot
- Graph
- source/tile navigation and controlled archive/restore actions

## Excluded by design
- no public controller
- no generic Analytics tutorial model
- no independent alert/business-event model
- no duplicated branch master
- no external API/authentication transport
- no Spreadsheet/Cohort/Gantt fabrication
- no transaction-owner model inheritance

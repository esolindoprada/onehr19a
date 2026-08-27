# OneHR Appraisal

Enterprise Performance Management for OneHR NEW on Odoo 19 Community Edition.

This Direct Full Addon Build replaces the supplied generic tutorial scaffold and
implements the authoritative three-model Appraisal contract:

- `onehr.appraisal.cycle`
- `onehr.appraisal.form`
- `onehr.appraisal.score`

Hard dependencies are exactly `onehr_corehr` and `onehr_security`.
Learning and Analytics remain soft/downstream integrations.

Capabilities include OKR/KPI target templates, annual/biannual/quarterly/custom cycles,
self/manager/peer review, weighted scoring, consolidation, rating distribution,
employee acknowledgement, IDP/development actions, KPI CSV import, result CSV export,
QWeb PDF, deadline reminders and governed downstream service contracts.

## Installation
Replace the entire old `onehr_appraisal` folder with this build. Do not merge old tutorial files.
Restart Odoo, Update Apps List, then install OneHR Appraisal.

## Source acceptance
Run:

`python tools/source_acceptance.py`

A source PASS never means Windows runtime completion. Follow
`docs/WINDOWS_RUNTIME_ACCEPTANCE.md`.

## Enterprise guardrail
`docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md` is mandatory.
Codex is a bounded implementation worker only: maximum two attempts for a proven source
task, same root cause repeated at most once.

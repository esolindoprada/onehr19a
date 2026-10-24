# OneHR Analytics — Project Identity Preflight

PROJECT: OneHR NEW  
ADDON: `onehr_analytics`  
TARGET: Odoo 19 Community Edition  
TASK: `ONEHR-ANALYTICS-DIRECT-FULL-20260831`  
ATTEMPT: `1 / 2`

## Authoritative inputs
- Root OneHR Enterprise Development Guardrail v1.
- Latest user-supplied OneHR workspace.
- OneHR Analytics product description embedded in the supplied addon.
- Current accepted OneHR sibling service contracts and ownership boundaries.
- Odoo 19 CE native ORM/security/view behavior.

## Supplied target baseline
The target addon is a generic Odoo tutorial scaffold: version `0.1`, hard dependency only
`base`, commented tutorial model/controller/views/demo, and broad placeholder
`base.group_user` full CRUD. There is no accepted Analytics business implementation in that
scaffold to preserve.

## Approved Analytics contract
Persistent models exactly:
- `onehr.analytics.tile`
- `onehr.kpi.snapshot`

Abstract utility exactly:
- `onehr.mixin.analytics`

Hard dependencies exactly:
- `onehr_security`

Optional/soft providers include Workforce, Recruitment, Attendance, Time Off, Learning,
Payroll Bridge, Appraisal, Career/Succession, and Discipline when installed and when the
calling Analytics operator also satisfies the source addon's own access authority.

## Change classification
`BASELINE_CLASSIFICATION: ADDON_SOURCE_FAILURE`

The tutorial scaffold is replaced as one coherent addon. No sibling source is modified.

`PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD`

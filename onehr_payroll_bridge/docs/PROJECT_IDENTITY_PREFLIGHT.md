# OneHR Payroll Bridge — Project Identity Preflight

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

- **PROJECT:** OneHR NEW
- **ADDON:** `onehr_payroll_bridge`
- **TARGET PLATFORM:** Odoo 19 Community Edition
- **DELIVERY METHOD:** Direct Full Addon Build
- **AUTHORITATIVE ARCHITECTURE:** OneHR Enterprise Architecture v2
- **AUTHORITATIVE REGISTRY:** OneHR Master Model Registry v1
- **PRODUCT BASELINE:** OneHR 25 Addons Specification for Odoo 19 CE
- **FUNCTIONAL BENCHMARK:** Oracle HRMS Enterprise / Workforce Management guidance where compatible with frozen OneHR ownership
- **CURRENT SOURCE BASELINE:** latest complete OneHR workspace dump supplied by the user on 20 Aug 2026
- **ROOT HARD GATE:** `ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md`
- **CODEX ROLE:** bounded implementation worker only

## Verified baseline

The supplied `onehr_payroll_bridge` is a generic tutorial scaffold: version `0.1`,
`base`-only dependency, placeholder controller/model/demo/views, and broad
`base.group_user` CRUD. It contains no accepted payroll business implementation to
preserve.

Preservation therefore targets the approved product/registry contract and accepted
sibling integration boundaries rather than the tutorial placeholder.

## Approved target responsibility

The product baseline identifies exactly three Payroll Bridge core models:

1. `onehr.payroll.bridge.config`
2. `onehr.payroll.export`
3. `onehr.payroll.import`

Hard dependencies are exactly:

- `onehr_corehr`
- `onehr_security`

Payroll Bridge owns interchange configuration, frozen source export evidence, vendor
result import/revision evidence, reconciliation, cost summaries and stable adapter
payloads.

## Explicitly outside ownership

- payroll calculation engine, salary rules and payslip calculation;
- Indonesian PPh21/BPJS/THR localization;
- accounting journals, GL posting and analytic master ownership;
- API keys, OAuth/SSO, public routes, webhooks and retry queues;
- attendance/time-off/discipline canonical transactions;
- employee, department, job, grade and position masters.

## Allowed change

Full registry-preserving replacement of the generic scaffold with the approved
enterprise implementation, including professional UI, security, audit/history,
CSV interchange, reconciliation, scheduling, reports, tests and evidence.

## Forbidden change

No new unapproved canonical payroll models, no hard dependency drift, no broad internal
user payroll access, no sensitive Core HR role implication, no sibling-source rewrite,
no accounting/API credential ownership, no tax-localization logic, and no history
weakening to make runtime pass.

`PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_SOURCE_BUILD`

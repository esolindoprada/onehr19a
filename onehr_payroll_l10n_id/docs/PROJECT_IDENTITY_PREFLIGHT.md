# OneHR Payroll Localization Indonesia — Project Identity Preflight

## PROJECT IDENTITY PREFLIGHT — HARD GATE 0

- **PROJECT:** OneHR NEW
- **ADDON:** `onehr_payroll_l10n_id`
- **TARGET:** Odoo 19 Community Edition
- **DELIVERY METHOD:** Direct Full Addon Build
- **AUTHORITATIVE ARCHITECTURE:** OneHR Enterprise Architecture v2
- **AUTHORITATIVE REGISTRY:** OneHR Master Model Registry v1
- **PRODUCT BASELINE:** OneHR 25 Addons Specification for Odoo 19 CE
- **CURRENT SOURCE BASELINE:** latest complete OneHR workspace supplied 20 Aug 2026
- **ROOT GUARDRAIL:** OneHR Enterprise Development Guardrail v1
- **CODEX ROLE:** Bounded implementation worker only

## Verified current target

The uploaded target addon is still the generic Odoo tutorial scaffold:

- version `0.1`;
- `base`-only dependency;
- placeholder commented controller/model;
- generic views/templates/demo;
- no Indonesian payroll-localization business implementation.

Therefore the approved preservation target is the OneHR product/Registry contract and
accepted downstream/upstream integration boundaries, not tutorial placeholder code.

## Approved product contract

- Exactly one core model: `onehr.payroll.l10n.param`.
- Hard dependency exactly `onehr_payroll_bridge`.
- PPh21 / PTKP / gross or gross-up parameters.
- BPJS Kesehatan and BPJS Ketenagakerjaan parameters.
- THR prorata and THR-calendar parameters.
- JSON/CSV parameter interchange.
- Parameter/historical recap.
- Hook/service payload to Payroll Bridge/external payroll.
- Security ownership: Payroll Manager.
- Workflow: **none — configuration only**.

## Forbidden changes

No additional statutory child/staging/wizard models; no payroll-engine/payslip ownership; no
employee tax-identity ownership; no accounting/payment ownership; no public API/controller or
credential ownership; no reverse hard dependency to later addons; no sibling-source rewrite.

`ROOT_CAUSE_CLASSIFICATION: ADDON_SOURCE_FAILURE`

`PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_SOURCE_BUILD`

# OneHR Base — Project Identity Preflight

PROJECT: OneHR NEW

ADDON: onehr_base

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1.
- Approved 25-addon topology.
- Latest corrected `onehr_base` source after the Odoo 19 plain-mixin compatibility repair.
- OneHR Enterprise Development Guardrail v2 — Direct Full Addon Build.
- Odoo 19 CE native-first ownership and official Odoo 19 technical behavior.

PRESERVATION RULE:
- Exactly 19 approved Registry rows for `onehr_base`.
- Odoo-native first for `hr.department`, `hr.job`, `hr.work.location`.
- No `onehr.employee`, `onehr.org.unit`, `onehr.job`, or `onehr.location`.
- Preserve effective dating, company integrity, checklist historical evidence,
  lifecycle seed codes, security intent, and downstream extension hooks.
- Hard dependencies remain exactly `hr`, `mail`.

ALLOWED CHANGE:
- Coherent Direct Full Addon Build.
- Odoo 19 compatibility hardening.
- Human-friendly refactoring without loss.
- Derived smart-button count fields and server actions on approved models.
- Advanced professional UI/UX, tests and documentation.
- `@api.ondelete(at_uninstall=False)` hardening for historical deletion protection.

FORBIDDEN CHANGE:
- New business model without Registry approval.
- Model deletion/merge/move/ownership change.
- Hard dependency change.
- Cross-addon edits.
- Security/effective-dating/history weakening.
- Parallel canonical HR masters.
- Codex architecture or simplification decisions.

CURRENT VERIFIED STATUS:
- Previous bounded source repair passed preservation/static gates.
- This Direct Full Build v1 is a new coherent source package.
- Source acceptance can be executed in this package.
- Windows/Odoo runtime acceptance for this exact build is PENDING until executed
  in the target environment.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD

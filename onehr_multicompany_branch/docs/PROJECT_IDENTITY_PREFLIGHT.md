
# OneHR Multicompany & Branch — Project Identity Preflight

## HARD GATE 0 — PROJECT IDENTITY PREFLIGHT

- PROJECT: OneHR NEW
- ADDON: `onehr_multicompany_branch`
- TARGET PLATFORM: Odoo 19 Community Edition
- DELIVERY METHOD: Direct Full Addon Build
- AUTHORITATIVE ARCHITECTURE: OneHR Enterprise Architecture v2
- AUTHORITATIVE REGISTRY: OneHR Master Model Registry v1
- PRODUCT BASELINE: OneHR 25 Addons Specification for Odoo 19 CE
- FUNCTIONAL BENCHMARK: Oracle HRMS Enterprise / Workforce Management Guide where applicable
- ROOT GUARDRAIL: `ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md`, SHA-256 `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`
- AUTHORITATIVE CURRENT SOURCE CONTEXT: latest complete `onehr19a(20260908-124356).md` workspace dump supplied by the user on 8 Sep 2026

## Preservation rule

The original `onehr_multicompany_branch` folder is a generic scaffold, not an approved business model. Its historical feature intent is preserved where compatible: branch isolation, explicit user branch scope, default branch, central visibility, branch master, company/user extension, quick branch selection, and reusable branch helpers.

The scaffold placeholder model `onehr_multicompany_branch.onehr_multicompany_branch` is deliberately NOT created because it is absent from the Master Model Registry. The approved persistent master is `onehr.branch`.

The current `onehr_security` branch-extension contracts are mandatory integration points and are not rewritten in the sibling addon:

- `onehr.user.role._branch_scope_overlap_domain()`
- `onehr.user.role._branch_scope_label()`
- `res.users._onehr_branch_scope_assignment_domain()`
- branch-aware extension of effective OneHR group reconciliation

## Allowed change

For repair `19.0.1.0.1`: change only `onehr_multicompany_branch`; close the proven cross-model branch read-authority defect for Odoo Technical Admin and OneHR Security Manager/Admin; audit Users / Role Assignment branch surfaces; add generic comodel-read source gate and runtime regressions. The prior Direct Full architecture remains frozen.

## Forbidden change

- no sibling addon source edits;
- no reverse dependency from `onehr_security` to branch;
- no new legal-company master replacing `res.company`;
- no broad `base.group_user` CRUD;
- no raw group/company entitlement bypass;
- no deletion/simplification of the security extension contract;
- no unregistered persistent/transient business model;
- no arbitrary JavaScript/systray complexity merely for appearance;
- no claim of completion based only on static/test PASS.

## Current verified status

The `19.0.1.0.1` bounded repair is source-reviewed and may be packaged only after the updated static gate passes. Odoo Windows upgrade, the five new cross-model runtime regressions, repeated upgrade, post-upgrade Users/Role Assignment smoke and final enterprise completeness remain PENDING until separately executed.



## Runtime Repair Attempt 2 — 19.0.1.0.2

The 2026-09-09 Odoo runtime log proves a distinct/incompletely addressed source defect inside the same approved Users governance path: uid 2 reaches `res.users.web_search_read` but lacks read ACL on `onehr.user.role`. Composite-source inspection shows the same Users summary/search path also reaches `onehr.role`, `onehr.sod.conflict.log`, and `onehr.audit.log`. Attempt 2 therefore closes the entire current dependency graph before another native rerun. The write scope remains `onehr_multicompany_branch/**`; sibling source remains frozen.

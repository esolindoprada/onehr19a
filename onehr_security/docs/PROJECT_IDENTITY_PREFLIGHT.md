
# OneHR Security — Project Identity Preflight

PROJECT: OneHR NEW

ADDON: onehr_security

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1.
- Approved OneHR 25-addon topology.
- Latest uploaded OneHR workspace/source dump.
- Accepted onehr_base native-first contract.
- OneHR Enterprise Development Guardrail v2 — Direct Full Addon Build.
- Official Odoo 19 security/res.users/res.groups behavior.

PRESERVATION RULE:
- Exactly these registry rows are owned/extended here:
  1. `res.users` — INHERIT_ODOO — ED0
  2. `onehr.role` — NEW — ED1
  3. `onehr.user.role` — NEW — ED1
  4. `onehr.sod.matrix` — NEW — ED1
  5. `onehr.sod.conflict.log` — NEW — ED3
  6. `onehr.audit.log` — NEW — ED3
- Odoo `res.users` and `res.groups` remain canonical.
- `onehr.branch` remains owned by `onehr_multicompany_branch`.
- Security must work without the branch addon.
- Hard dependencies remain exactly `onehr_base`, `mail`.
- Preserve role management, provisioning, company/branch-ready scope, SoD,
  security audit, sensitive-access foundation and compliance visibility.

ALLOWED CHANGE:
- Replace the generic scaffold with a complete enterprise implementation.
- Odoo 19 compatibility and least-privilege hardening.
- Effective role assignment and reconciliation.
- Advanced professional UI on approved models/native extensions.
- Tests, documentation, source/runtime acceptance tooling.
- Extension hooks for later branch narrowing without reverse dependency.

FORBIDDEN CHANGE:
- No new OneHR persistent/transient business model outside Registry approval.
- No `onehr.branch` definition.
- No hard dependency on `onehr_multicompany_branch`.
- No duplicate user/group identity model.
- No `base.group_user` full CRUD on OneHR security models.
- No UI-only security.
- No automatic grant of unrelated future medical/discipline secrets.
- No cross-addon source write.
- No Codex architecture or simplification.
- No endless retry loop.

CURRENT VERIFIED STATUS:
- Uploaded source was a generic scaffold with version 0.1, base-only dependency,
  placeholder model/controllers/views/demo and a broad scaffold ACL.
- The historical application description stated enterprise intent for roles,
  provisioning, record rules, audit, SoD, PII/security policy and compliance.
- This delivery reconstructs that intent inside the frozen Architecture/Registry.
- Source acceptance is executed on this package.
- Exact Odoo/Windows runtime acceptance remains PENDING until user execution.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_SOURCE_BUILD

# onehr_document — Project Identity Preflight

PROJECT: OneHR NEW

ADDON: onehr_document

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1.
- Approved OneHR 25-addon topology and dependency ownership.
- Latest user-provided OneHR workspace dump dated 2026-08-14.
- Accepted contracts from `onehr_base`, `onehr_security`, `onehr_corehr`,
  `onehr_workflow_approval`, and `onehr_multicompany_branch`.
- Project-root `ONEHR_ENTERPRISE_DEVELOPMENT_GUARDRAIL.md`.
- Odoo 19 CE native `ir.attachment`, `ir.actions.report`, ORM access-check,
  mail/thread/activity and security behavior.

PRESERVATION RULE:
- Preserve document-library, category/classification, numbering, effective
  validity, template versioning, expiry/reminder, issue/sign/archive workflow,
  generation, e-sign metadata, reports and audit intent from the historical
  scaffold description.
- Preserve exactly the eight approved Registry rows owned by `onehr_document`.
- `onehr.document` / `onehr.document.version` are canonical HR document facts.
- Binary payload remains on Odoo attachment-backed fields; other OneHR addons
  reference document records rather than copying attachments.
- `hr.employee` remains canonical employee identity.
- Branch remains owned by `onehr_multicompany_branch`.
- Approval evidence remains owned by `onehr_workflow_approval`.
- External provider integration remains soft through `onehr_integrations_api`.

ALLOWED CHANGE:
- Full replacement of the generic scaffold.
- Registry-preserving Odoo 19 reconstruction.
- Advanced enterprise UI, report, expiry governance, secure source-reference
  validation, tests and documentation.
- Safe bounded template-variable rendering without executable stored code.
- Narrow integration hooks for future `onehr_integrations_api` adaptation.

FORBIDDEN CHANGE:
- No `onehr.employee.document`.
- No new document-tag model without Registry approval.
- No `res.config.settings` extension because it is not a Registry row owned by
  this addon.
- No direct hard dependency on `onehr_base`, `onehr_workflow_approval`,
  `onehr_multicompany_branch`, `portal`, or `onehr_integrations_api`.
- No provider credentials in `onehr.esign.transaction`.
- No broad `base.group_user` custom-model ACL.
- No portal/controller route that could bypass attachment/model security.
- No branch ownership.
- No copy of HR document binaries into sibling domain tables.
- No Codex architecture/simplification/deletion/dependency decision.
- No sibling-addon source write.

CURRENT VERIFIED STATUS:
- The uploaded `onehr_document` is a generic scaffold (`version=0.1`,
  `depends=['base']`) with commented placeholders and broad base-user CRUD.
- This Direct Full Build replaces the generic scaffold with the approved
  Registry implementation.
- Source acceptance is executable inside this package.
- Windows/Odoo runtime acceptance remains PENDING until run on the user's
  target environment.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_SOURCE_BUILD

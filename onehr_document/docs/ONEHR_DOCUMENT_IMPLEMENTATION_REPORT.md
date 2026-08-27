# onehr_document — Direct Full Addon Build v1

## Delivery method

This is one coherent Direct Full Addon Build. Codex was not used as architect,
builder or autonomous repair engine.

## Enterprise architecture implemented

- Canonical document facts are `onehr.document` and `onehr.document.version`.
- Category, document, document version, template, template version, e-sign
  transaction and two approved wizards match the Master Model Registry.
- Hard dependencies remain exactly `onehr_corehr`, `onehr_security`, `mail`.
- Odoo attachment mechanisms store binary evidence; there is no parallel binary
  repository.
- `onehr_corehr` employee ownership is referenced, not duplicated.
- Approval/branch/provider ownership stays in its approved sibling/soft layer.

## Odoo 19 hardening

- No obsolete generic controllers/demo scaffold.
- No broad `base.group_user` custom-model ACL.
- No public attachment/download controller.
- Source business records use `check_access("read")`.
- Stored template variables are bounded content tokens, not eval/safe_eval.
- QWeb report action uses the Odoo 19 `ir.actions.report` contract.
- Issued document versions and e-sign evidence use uninstall-safe
  `@api.ondelete(at_uninstall=False)` protection.
- No business-model `sudo()` authorization bypass.

## Enterprise UX

The addon contains advanced but purposeful interactions:
- document and version statusbars;
- template-version and e-sign statusbars;
- smart buttons;
- controlled header actions;
- body-form expiry reminder action;
- One2many/list operational row buttons;
- professional list/search coverage;
- expiry and e-sign pivot/graph analysis;
- chatter/activity history.

## Security/privacy

- Global company rules are the legal partition.
- Employee self-access is restricted to own employee-visible internal records.
- Officer/Manager operates internal/confidential records.
- Compliance can read restricted evidence but does not receive write power.
- Restricted mutation therefore requires explicit combined authority.
- Provider credentials are forbidden from e-sign metadata.
- Attachment-backed binaries inherit the protected document-version ownership
  contract and no public bypass route exists.

## Status

SOURCE_DIRECT_FULL_BUILD: READY_FOR_SOURCE_ACCEPTANCE
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_DOCUMENT_MOVE_FORWARD_READY: NO

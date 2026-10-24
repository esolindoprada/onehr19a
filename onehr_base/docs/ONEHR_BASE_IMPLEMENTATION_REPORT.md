

# OneHR Base — Direct Full Addon Build v1

## Delivery Method

This package is built as one coherent Direct Full Addon Build. It is not the
output of an open-ended Codex patch/retry loop. Codex is reserved only for a later
bounded implementation repair if runtime evidence proves a specific defect.

## Architecture Preserved

- `hr.department` remains canonical organization hierarchy.
- `hr.job` remains canonical generic job catalogue.
- `hr.work.location` remains canonical work-location master.
- `onehr.position` represents an authorized enterprise seat and capacity, not a
  generic job and not assignment occupancy.
- Grades and grade steps are effective-dated OneHR-owned masters.
- Position hierarchies use explicit effective-dated versions and version-owned nodes.
- `ir.sequence` remains the numbering engine.
- Eligibility uses structured deterministic criteria, not stored executable code.
- Checklist execution freezes template facts and protects completed evidence.

## Odoo 19 Hardening

- No plain-Python helper class is used in Odoo model Python bases.
- Reusable native validity behavior is implemented with module-level helpers plus
  thin model methods.
- Completed-history deletion restrictions use `@api.ondelete(at_uninstall=False)`.
- UI uses Odoo 19 direct expression syntax for `invisible`/`readonly`.
- Tests remain tagged `post_install`, `-at_install`, `onehr_base`.

## Enterprise UI/UX

The build includes professional enterprise interaction patterns where they have a
real purpose: header actions, statusbars, smart buttons, body-form operational
action, One2many/list row actions, search/group-by views for every custom
persistent model, operational list columns, badges/decorations, notebooks,
ribbons and chatter on OneHR audited records.

## Security

- No broad custom-model access for `base.group_user`.
- HR Officer reads controlled master/configuration records and has explicit
  operational checklist create/write rights.
- HR Manager administers controlled master/configuration data.
- Company-aware models use allowed-company record rules.
- Completed checklist history/evidence is protected at model level.
- UI buttons do not use `sudo()` to bypass authorization.

## Status

SOURCE_DIRECT_FULL_BUILD: PASS
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_BASE_MOVE_FORWARD_READY: NO

## Binary Asset Preservation

The approved prior source preserved `static/description/icon.png`. The Direct Full
Build intentionally does not fabricate a replacement binary. The deployment helper
backs up and restores the existing icon into the new addon.

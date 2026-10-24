
# OneHR Portal Self-Service

Enterprise employee and manager self-service for OneHR NEW on Odoo 19 Community Edition.

This Direct Full Addon Build replaces the supplied tutorial scaffold and implements the
approved portal contract around exactly three persistent business models:

- `onehr.portal.request.type`
- `onehr.portal.request.stage`
- `onehr.portal.request`

Native/shared extensions are limited to `res.users` and `hr.employee`; transient decision
and bulk-action wizards do not create new persistent business masters.

Core capabilities include My HR, My Team, governed request lifecycle, manager/HR approval,
SLA monitoring, attachment/chatter evidence, profile-change approval, backend operational
views, portal dashboards and bounded soft integrations with Time Off, Learning, Document,
Appraisal, Payroll Bridge, Job Description, Policies & Procedures, SOP and Career/Succession.

## Installation

Replace the old `onehr_portal_self_service` tutorial folder with this complete addon.
Restart Odoo, Update Apps List, then install **OneHR Portal Self-Service**.

## Source acceptance

Run:

`python tools/source_acceptance.py`

Source acceptance is only a prerequisite. It does not prove Windows/Odoo runtime,
security, portal rendering, scheduler, upgrade or cross-addon completeness.

## Enterprise guardrail

`docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md` is mandatory. Codex is a bounded
implementation worker only: maximum two attempts for a proven implementation/repair task,
and the same root cause may repeat at most once.

## Runtime repair 19.0.1.0.1

Odoo 19 activation evidence proved that the Portal user-type external ID is
`base.group_portal`, not `portal.group_portal`. Release 19.0.1.0.1 applies only that
architecture-preserving compatibility correction, adds a regression gate/test, and keeps
all enterprise functionality and security boundaries intact.


## Explicitly approved new bounded repair task — 19.0.1.0.2

After the previous task correctly stopped at its two-attempt limit, the architecture/reviewer
explicitly approved a new bounded repair task on 2026-08-29. Runtime evidence from Odoo
`19.0.20251217` proved that `ir.actions.act_window` rejects the field `groups_id`.

Release `19.0.1.0.2` changes only the bound Bulk Request Decision action to the Odoo 19
field `group_ids`, preserves the Manager/HR visibility restriction, and adds source/runtime
regression checks. No Portal model, workflow, dependency, ACL, record rule, integration
contract, ownership boundary or enterprise feature is removed or widened.

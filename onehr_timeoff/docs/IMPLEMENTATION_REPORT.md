# OneHR Time Off — Direct Full Implementation Report

The supplied `onehr_timeoff` folder was a generic tutorial scaffold. This build replaces that scaffold with a full Time Off domain aligned to the OneHR 25-addon product baseline and the accepted OneHR sibling contracts.

The design deliberately creates exactly the three Time Off core business model names explicitly identified by the product baseline: `onehr.leave.type`, `onehr.leave.request`, and `onehr.leave.allocation`. It does not create a separate balance table, accrual-rule table, carry-over ledger or transient mass wizard because those extra model owners were not available as approved Registry rows in the supplied references.

`onehr.leave.type` is the policy master. It supports annual/sick/special/training/unpaid/other leave, paid/unpaid behavior, grade and length-of-service eligibility, notice/document/half-day controls, automatic monthly/annual accrual, first-year proration, seniority bonus, accrual cap, carry-over cap/expiry, negative-balance policy, and team-conflict warning/block rules. Activated policy facts are frozen and effective-date overlap is rejected so policy history is not silently rewritten.

`onehr.leave.allocation` is the entitlement evidence. It supports manual, opening-balance, accrual, carry-over, adjustment and mass-allocation sources. Used/available balance is derived from immutable allocation evidence and approved/done request reservations instead of destructively decrementing a master balance. Scheduler rows carry unique `source_key` values so repeated accrual/carry-over execution is idempotent. Mass allocation is a durable parent allocation record that generates durable employee child allocations; it opens modally and includes generated One2many row actions, preserving both professional UX and audit evidence without inventing a transient business model.

`onehr.leave.request` is the employee transaction. It calculates working-calendar duration, validates eligibility, overlapping leave, notice, document requirements, team capacity and entitlement. It integrates with `onehr.mixin.approvable`; the generic workflow engine owns approval routing/evidence while Time Off owns the business state and freezes the entitlement reservation only on final approval. Approval/cancellation/completion evidence is preserved. Approved/done requests feed balance, utilization and approval-lead analytics.

Security is model-level and least-privilege. Time Off User is self-service only; Time Off Manager is direct-report/team scoped and does not receive broad Core HR private-data authority; Time Off HR owns policy/allocation administration within allowed companies. No `base.group_user` custom CRUD and no business `sudo()` call is used.

Integration boundaries are explicit. Attendance is a soft validation hook, Payroll is a downstream paid/unpaid payload consumer, Analytics can consume KPI fields, and branch narrowing is left to the branch owner. No reverse hard dependency is introduced.

SOURCE_DIRECT_FULL_BUILD: BUILT
SOURCE_ACCEPTANCE: PASS (0 failures)
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_TIMEOFF_MOVE_FORWARD_READY: NO

## Odoo 19 Compatibility Correction v1.1 — 18 Aug 2026

Target runtime evidence on Odoo 19.0.20251217 proved that `ir.actions.report`
uses the security field `group_ids`, not `groups_id`. The Leave Request PDF
action was corrected accordingly. No report, security restriction, model,
workflow, dependency, field, business method, UI surface, or enterprise feature
was removed or weakened.

The source acceptance gate now validates this ORM field contract explicitly so
the same defect cannot pass XML-only validation again.

ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE
BOUNDED_REPAIR_ATTEMPT: 1
ARCHITECTURE_CHANGE: NONE
FUNCTIONAL_REDUCTION: NONE
SECURITY_REDUCTION: NONE

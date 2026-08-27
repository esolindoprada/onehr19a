# onehr_timeoff — Full Structural Inventory

## Persistent custom models

1. `onehr.leave.type`
   - leave category/type and effective policy;
   - paid/unpaid and allocation/approval requirements;
   - half-day/document/notice/max-duration controls;
   - grade and length-of-service eligibility;
   - monthly/annual accrual, seniority bonus, cap and first-year proration;
   - carry-over cap and expiry;
   - team-conflict warning/block policy;
   - current-year allocation/usage/balance/utilization KPIs.

2. `onehr.leave.request`
   - employee self-service leave request;
   - work-calendar-aware duration;
   - team-calendar conflict detection;
   - entitlement validation and frozen allocation reservation evidence;
   - generic OneHR Workflow Approval integration;
   - approval lead-time KPI and execution evidence;
   - supporting attachment;
   - stable attendance validation hook and payroll payload hook;
   - QWeb leave request report.

3. `onehr.leave.allocation`
   - manual/opening/accrual/carry-over/adjustment/mass entitlement evidence;
   - effective entitlement period and expiry;
   - dynamic used/available balance derived from approved/done leave evidence;
   - scheduler idempotency key;
   - durable mass allocation parent/children;
   - daily accrual/carry-over/request-completion scheduler.

## Odoo-native model extension

- `hr.employee`: Time Off request/allocation/current-leave counts and HR-only smart buttons. No canonical ownership change.

## Python source structure

- `models/leave_type.py` — policy/eligibility/accrual formula.
- `models/leave_request.py` — request workflow, balance reservation, conflict control and integration hooks.
- `models/leave_allocation.py` — entitlement ledger, mass allocation and scheduler.
- `models/native_extensions.py` — narrow employee navigation only.
- `models/authority_helpers.py` — explicit Time Off role checks.
- `models/action_helpers.py` — conventional action builders.

## Security

- Time Off User — own requests and own balances only.
- Time Off Manager — own + direct-report requests/balances/team calendar; no broad Core HR private-data grant.
- Time Off HR — company-scoped policy/allocation administration plus Core HR Officer authority.
- No custom ACL assigned to `base.group_user`.
- Company, self and direct-manager record rules are explicit.
- UI visibility is not relied upon as the security boundary.

## Data / automation

- leave request sequence;
- leave allocation sequence;
- daily idempotent accrual/carry-over/completion cron.

## UI

- List/Form/Search for all three custom models.
- Leave Request Calendar/Pivot/Graph.
- Leave Allocation Pivot/Graph.
- Statusbars, smart buttons, body actions, row actions and chatter.
- Persistent mass-allocation modal with One2many generated child rows and row buttons.
- Employee smart-button integration.
- QWeb PDF leave request evidence.

## Tests / tooling

- 20 post-install runtime test methods.
- `tools/source_acceptance.py` validates manifest, models, syntax/XML, ACL, no legacy `_sql_constraints`, no business `sudo()`, views, UI markers, contracts and docs.

LEGACY_SCAFFOLD_STATUS: REPLACED
CUSTOM_PERSISTENT_MODEL_COUNT: 3

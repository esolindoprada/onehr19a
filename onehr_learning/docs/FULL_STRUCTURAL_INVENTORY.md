# OneHR Learning — Full Structural Inventory

## Persistent business models
1. `onehr.learning.course` — catalog, curriculum text, prerequisites, level, pass/certificate policy.
2. `onehr.learning.session` — scheduled classroom/virtual/blended/self-paced delivery, capacity,
   waitlist, trainer/vendor, reminders, participant CSV import and result CSV export.
3. `onehr.learning.enrollment` — governed learner journey and generic approval source.
4. `onehr.learning.attendance` — training-session presence evidence (not `hr.attendance` ownership).
5. `onehr.learning.certificate` — certificate issue/expiry/revocation and printable evidence.
6. `onehr.learning.vendor` — training-provider-specific master linked optionally to `res.partner`.
7. `onehr.learning.budget` — L&D budget, burn, cost-per-learner and overrun policy.
8. `onehr.learning.cost.line` — planned/committed/actual/cancelled training cost evidence.

## Intentionally NOT created
- `onehr_learning.onehr_learning` tutorial placeholder.
- Course tag / curriculum line / portal staging / import wizard business tables.
- Duplicate employee, competency, work-attendance, payroll, leave, document or API-owner models.

## Hard dependencies
Exactly: `onehr_base`, `onehr_corehr`, `onehr_security`, `onehr_workflow_approval`.

## Soft downstream integrations
`onehr_attendance`, `onehr_timeoff`, `onehr_document`, `onehr_payroll_bridge`,
`onehr_portal_self_service`, `onehr_analytics`, `onehr_integrations_api`,
`onehr_multicompany_branch`.

## Technical structure
- models/: business files + small reusable helper/service extensions
- security/: groups, ACL and company/trainer record rules
- views/: one dedicated enterprise view file per business concern
- reports/: certificate and Learning summary QWeb outputs
- data/: sequences and governed reminder/expiry crons
- tests/: transaction/runtime tests for catalog, workflow, evidence, security and integrations
- tools/: source acceptance gate
- docs/: hard gates, integration contract, UI matrix, runtime checklist and completeness evidence

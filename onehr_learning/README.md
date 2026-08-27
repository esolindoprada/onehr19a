# OneHR Learning

Enterprise Learning & Development for OneHR NEW on Odoo 19 Community Edition.

This Direct Full Addon Build replaces the supplied generic tutorial scaffold. It provides
the approved course catalog, sessions, enrollment/approval, waitlist, training attendance,
assessments, certification, vendors, budgets/costs, reminders, reporting, import/export
and narrow downstream integration services.

## Hard dependencies
- onehr_base
- onehr_corehr
- onehr_security
- onehr_workflow_approval

## Persistent Learning models
Exactly eight:
`onehr.learning.course`, `onehr.learning.session`, `onehr.learning.enrollment`,
`onehr.learning.attendance`, `onehr.learning.certificate`, `onehr.learning.vendor`,
`onehr.learning.budget`, `onehr.learning.cost.line`.

## Main enterprise workflow
Draft → Requested → Approved → Enrolled → Attended → Passed/Failed → Certified.
Waitlisted, Rejected, Cancelled and No Show are governed operational branches.

## Installation
Copy/replace the complete folder as `onehr_learning` inside the OneHR addons path,
restart Odoo, Update Apps List, then install `OneHR Learning`.

Do not merge the old scaffold files into this build. Replace the target addon as one
consistent unit. Do not edit sibling addons for this installation.

## Acceptance
Run:
`python tools/source_acceptance.py`

A source PASS does not mean runtime completion. Follow
`docs/WINDOWS_RUNTIME_ACCEPTANCE.md` on the real Odoo 19 Windows instance.

## Guardrail
`docs/ENTERPRISE_DEVELOPMENT_GUARDRAIL.md` is a hard gate.
Codex is a bounded implementation worker only; maximum two attempts per proven source task.

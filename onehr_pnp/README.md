# OneHR Policies & Procedures (PnP)

Enterprise policy governance for OneHR NEW on Odoo 19 Community Edition.

Persistent PnP business models are exactly:

- `onehr.policy`
- `onehr.policy.ack`
- `onehr.policy.evidence`

`res.config.settings` is extended only as the approved transient configuration surface.

Hard dependencies are exactly:

- `onehr_security`
- `onehr_document`
- `onehr_workflow_approval`

Workflow:
Draft → Approval → Approved → Published → Review → Archived,
with Rejected as an approval exception state.

Capabilities include controlled policy version rows/change log, targeted publication
by company/department/job/specific employee, employee acknowledgement, compliance
evidence, review scheduling/reminders, OneHR Workflow Approval integration,
OneHR Document archive snapshots, compliance/evidence reporting, and downstream
Portal/Analytics/API service contracts.

Operational SOP ownership is **not duplicated** here. When `onehr_sop` is installed,
PnP can reference SOP codes through a soft runtime service boundary. SOP content,
SOP versions and SOP acknowledgement remain owned by `onehr_sop`.

Source/static acceptance does not mean Windows runtime acceptance. Follow
`docs/WINDOWS_RUNTIME_ACCEPTANCE.md` before declaring the addon frozen.

# Latest Workspace Alignment — 2026-09-01

Authoritative current workspace reference: `onehr19a.md`, uploaded/modified `2026-09-01T10:41:30Z`. The root guardrail in that workspace is `ONEHR-EDG-V1`; its companion SHA file records `9E7614A6BC5459D8672ECC5F655738FCE0FC0053252EDDF6D8D003655B945A55`. No raw workspace dump checksum is invented inside this addon.

The latest supplied OneHR workspace still shows `onehr_retirement_offboarding` as a generic scaffold while its product description calls for a real enterprise offboarding module with four core models, Requested → In Progress → Completed → Closed orchestration, generated clearance tasks, exit interview, access revocation, final benefit bridge, SLA, audit and soft coupling to wider OneHR.

Current OneHR Employment Contract has already frozen a crucial boundary: Employment Contract owns legal contract termination and base TERMINATION checklist evidence, while Retirement/Offboarding owns broader exit orchestration and employee archival is not performed by contract termination. This build follows that boundary.

Current Workflow Approval exposes `onehr.mixin.approvable`; the source addon owns state/execution while Workflow Approval owns routing and decision evidence. This build uses that contract rather than implementing a second approval engine.

Current OneHR base exposes `onehr.mixin.audit`, so all four persistent models inherit the accepted chatter/activity foundation.

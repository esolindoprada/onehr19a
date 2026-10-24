
# OneHR Workflow Approval — Project Identity Preflight

PROJECT: OneHR NEW

ADDON: onehr_workflow_approval

AUTHORITATIVE BASELINE:
- OneHR Enterprise Architecture v2.
- OneHR Master Model Registry v1.
- Approved 25-addon topology.
- OneHR 25 Addons Specification functional intent.
- Latest user-supplied OneHR source export; the current workflow addon itself is generic scaffold.
- OneHR Enterprise Development Guardrail.
- Odoo 19 Community Edition native technical behavior.

PRESERVATION RULE:
- Preserve exactly eight Registry rows.
- Generic approval engine owns approval configuration/path/evidence, not source business state.
- Preserve matrix/threshold/role routing, sequential+parallel routing, delegation/reassign,
  SLA reminder/escalation, self-approval guard, quorum/multi-eyes, resubmit/cancel,
  chatter/activity, immutable evidence and SLA/KPI intent.
- Hard dependencies remain exactly `onehr_security`, `mail`.
- No reverse dependency to transaction owners or `onehr_analytics`.

ALLOWED CHANGE:
- Direct Full Addon Build replacing generic scaffold.
- Odoo 19 compatibility hardening.
- Registry-preserving enterprise implementation.
- Human-friendly source decomposition, professional UI/UX, tests and governance docs.
- Safe structured conditions and narrow source hooks.
- Narrow documented routing/evidence sudo only where broad ACL grants would be less secure.

FORBIDDEN CHANGE:
- New business/Registry model outside the eight approved rows.
- Source transaction ownership/execution in approval engine.
- Stored eval/safe_eval/Python routing criteria.
- Broad custom-model `base.group_user` ACL.
- Security/effective-dating/history weakening.
- Sibling source edits.
- Codex architecture/simplification/dependency decisions.

CURRENT VERIFIED STATUS:
- User requested `onehr_workflow_approval` after `onehr_corehr` was temporarily accepted.
- Direct Full Build source previously passed its source acceptance.
- Windows install on Odoo 19.0.20251217 reached registry field setup and failed on
  `onehr.approval.rule.model_id` because Odoo 19 forbids `ondelete="restrict"`
  when the comodel is `ir.model`.
- Root cause is classified ODOO_VERSION_COMPATIBILITY_FAILURE.
- This corrected build changes the required metadata relation to
  `ondelete="cascade"`, preserves the approved architecture/Registry, and adds a
  source-acceptance regression gate plus an assertion inside an existing runtime test.
- Fresh-install runtime retry is PENDING.

PREFLIGHT_RESULT: PASS_FOR_DIRECT_FULL_BUILD

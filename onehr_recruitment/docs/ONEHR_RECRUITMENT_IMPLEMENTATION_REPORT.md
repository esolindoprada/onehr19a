# onehr_recruitment — Direct Full Addon Build v1

## Delivery

Built as one coherent Direct Full Addon Build. Codex was not used.

## Enterprise architecture

The addon extends Odoo-native `hr.applicant`, `hr.recruitment.stage`, `hr.job` and `hr.talent.pool`; it does not create parallel canonical masters. Seven OneHR-owned persistent models implement governed requisitions, versioned interview definitions, interview evidence, offers, preboarding and ED4 source metrics.

## Main business flow

Requisition Draft → Pending Approval → Approved → Recruiting → Filled/Cancelled. Native applicants are linked to requisitions and continue through Odoo's pipeline. Structured interview sessions freeze the template identity and collect per-rater final score evidence. Offer Draft → Pending Approval → Approved/Rejected → Sent → Accepted/Declined/Withdrawn/Expired. Accepted offers can start preboarding. Preboarding uses native Odoo employee conversion and the base-owned HIRE checklist rather than creating duplicate employee/onboarding masters.

## Security

Three OneHR recruitment privilege levels are implemented. Custom governed models have no broad `base.group_user` ACL and no unlink ACL. Company boundaries are global rules. Hiring Manager rows are assignment-scoped. Offer compensation has additional field/UI restriction. Creating a new employee from an applicant is Recruitment Manager-only. Business-source `sudo()` is absent.

## UI

Every custom persistent model has list/form/search. Advanced interactions include statusbars, lifecycle header actions, smart buttons, body-form actions, One2many row actions, calendar, pivot/graph analytics, chatter and immutable-evidence ribbons where they serve a business purpose.

## Integration

Workflow Approval is a hard dependency for requisition/offer approval evidence. OneHR Document remains a soft integration for governed offer-letter generation. Hire-domain owners remain downstream extension contracts. Branch and API addons are not reverse hard dependencies.

## Verification status

Source/static acceptance is executed by `tools/source_acceptance.py`.
Windows/Odoo database runtime acceptance remains pending until run on the user's target Odoo 19 environment.

CODEX_EXECUTED: NO
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO

## Runtime Repair Attempt 2/2 — Odoo 19 Properties Definition

The first source-level Windows activation failure after environment recovery reached
`onehr.interview.score.scorecard_values`. Odoo 19 rejects the previous multi-hop
Properties definition `session_id.template_id.scorecard_definition`.

Repair `19.0.1.0.1` uses the already-owned related Many2one and preserves the same
template container:

`definition="template_id.scorecard_definition"`

`tools/source_acceptance.py` now carries a regression gate for the Odoo 19
`fields.Properties` one-dot definition contract.

`ROOT_CAUSE_CLASSIFICATION: ODOO_VERSION_COMPATIBILITY_FAILURE`  
`ATTEMPT: 2/2`  
`WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST`  
`ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO`

## Reviewer-Authorized Follow-up Repair — 19.0.1.0.2

After the prior task stopped at its bounded retry limit, the reviewer explicitly authorized
a new follow-up task for the distinct Preboarding search-view validation defect.

The `Pending Checklist Tasks` search filter no longer filters the non-searchable display
counter `checklist_pending_task_count`. It now follows the canonical checklist relation and
searches `checklist_instance_id.task_ids.state = pending`, preserving identical business
meaning without changing models, fields, ownership, dependencies, security or workflow.

A targeted source-acceptance regression gate now requires that exact filter and rejects future
Preboarding domains that use the non-searchable counter.

`FOLLOWUP_TASK: ONEHR-RECRUITMENT-FOLLOWUP-PREBOARDING-SEARCH-20260903`  
`FOLLOWUP_ATTEMPT: 1/2`  
`WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST`  
`ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO`

## Reviewer-Authorized Follow-up Repair — 19.0.1.0.3

Task: `ONEHR-RECRUITMENT-FOLLOWUP-SEARCH-DOMAINS-20260903`  
Attempt: `1 / 2` for this separately reviewer-authorized follow-up task.  
Root cause: `ODOO_VERSION_COMPATIBILITY_FAILURE`.

The Odoo 19 registry reached the native Applicant search view and rejected
`onehr_latest_offer_state` because it was a non-stored computed field. The reviewer
authorized a bounded audit of all remaining Recruitment search-domain defects.

The repair preserves the exact business meaning "latest offer is accepted" by keeping
the Applicant filter on `onehr_latest_offer_state` and making that computed business
fact stored/indexed/searchable. Its compute now invalidates on `onehr_offer_ids.state`
so an offer lifecycle change refreshes the searchable value.

The Job search filter no longer filters the display-only
`onehr_open_requisition_count`. It follows the authoritative requisition relation and
the same open lifecycle states (`approved`, `recruiting`) used by the counter.

`tools/source_acceptance.py` now performs a generic AST/XML audit over every domain
attribute in Recruitment views and rejects target-local computed/related domain leaves
that are not stored/searchable. The 19.0.1.0.3 source audit scans 22 domain attributes
and 27 domain leaves with no target-local non-searchable leaf remaining.

No model ownership, hard dependency, security group, ACL, record rule, workflow,
enterprise feature, custom-model count, native-inherit count, or runtime-test inventory
is changed.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST`  
`ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO`

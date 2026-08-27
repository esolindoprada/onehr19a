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

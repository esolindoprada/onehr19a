# OneHR Recruitment — Reviewer-Authorized Follow-up Runtime Repair 19.0.1.0.3

TASK: `ONEHR-RECRUITMENT-FOLLOWUP-SEARCH-DOMAINS-20260903`  
ATTEMPT: `1 / 2` for this explicitly reviewer-authorized follow-up task  
DATE: `2026-09-03`  
TARGET_PLATFORM: `Odoo 19 Community Edition`  
SOURCE_WRITE_SCOPE: `onehr_recruitment` only  
INPUT_BASELINE: `onehr19a(20260903-110216).md`  
PREVIOUS_VERSION: `19.0.1.0.2`  
REPAIR_VERSION: `19.0.1.0.3`  
ROOT_CAUSE_CLASSIFICATION: `ODOO_VERSION_COMPATIBILITY_FAILURE`

## Reviewer authorization

The reviewer explicitly authorized a new bounded follow-up repair covering all
remaining Odoo 19 unsearchable Recruitment search-domain defects, with four mandatory
requirements:

1. make `onehr_latest_offer_state` searchable without changing "latest offer" semantics;
2. replace the `onehr_open_requisition_count` search domain with a searchable,
   semantics-equivalent relation domain;
3. audit all Recruitment view search domains; and
4. add a generic regression gate.

The reviewer explicitly prohibited changes to architecture, model ownership,
dependencies, security, workflow, ACLs, record rules, and enterprise features.

## Runtime evidence

Odoo reached `views/native_recruitment_views.xml` and rejected the Applicant search
filter:

`[('onehr_latest_offer_state', '=', 'accepted')]`

because `onehr_latest_offer_state` was computed, non-stored, and had no custom
`search=` method.

Proactive source audit also found the Job search filter:

`[('onehr_open_requisition_count', '>', 0)]`

where `onehr_open_requisition_count` is another display-only non-stored computed field.

## Bounded correction

### Applicant — latest accepted offer

The filter remains:

`[('onehr_latest_offer_state', '=', 'accepted')]`

so its business meaning is not weakened to "any historical offer was accepted".

`onehr_latest_offer_state` remains computed from the most recently created
`onehr.offer`, but is now `store=True` and `index=True`. The shared compute dependency
adds `onehr_offer_ids.state`, ensuring offer lifecycle changes invalidate and refresh
the stored searchable value.

### Job — open requisitions

The filter becomes:

`[('onehr_requisition_ids.state', 'in', ('approved', 'recruiting'))]`

This is semantics-equivalent to the existing display counter because
`onehr_open_requisition_count` counts those exact two requisition lifecycle states.
The counter itself remains a non-stored display field.

## Generic regression prevention

`tools/source_acceptance.py` now:

- parses all Recruitment `views/*.xml`;
- inspects every `domain` attribute;
- extracts domain leaves through Python AST without evaluating domain code;
- builds a target-local field registry from the Recruitment Python source;
- resolves locally-owned relational paths when possible;
- rejects a computed or related target-local domain leaf unless it is stored or has
  an explicit search method;
- verifies the exact Applicant latest-offer semantics;
- verifies the exact Job open-requisition relation domain; and
- retains the earlier Preboarding and `fields.Properties` Odoo 19 regression gates.

Final source audit result:

- Recruitment domain attributes scanned: `22`
- Recruitment domain leaves scanned: `27`
- Target-local non-searchable domain leaves remaining: `0`
- Source acceptance failures: `0`

## Preservation evidence

Unchanged by this task:

- hard dependencies: exactly `onehr_corehr`, `onehr_security`,
  `onehr_workflow_approval`, `hr_recruitment`;
- seven OneHR-owned persistent Recruitment models;
- four Odoo-native Recruitment extensions;
- 21 custom-model ACL rows;
- all Recruitment record rules;
- Recruitment security groups and privilege hierarchy;
- requisition/interview/offer/preboarding workflows;
- existing effective-dating/history behavior;
- 20 post-install runtime test methods;
- enterprise List/Form/Search/Kanban/Calendar/Pivot/Graph surfaces and action buttons.

No sibling OneHR addon source is changed by this package.

## Runtime status

Source/static acceptance is PASS for runtime retest only.

`WINDOWS_RUNTIME_ACCEPTANCE: PENDING_RETEST`  
`ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO`

# OneHR Recruitment — Full Structural Inventory

## Manifest

- Name: OneHR Recruitment
- Version: `19.0.1.0.3`
- Hard dependencies: `onehr_corehr`, `onehr_security`, `onehr_workflow_approval`, `hr_recruitment`
- Application: yes

## Python source structure

- `models/action_helpers.py` — pure act-window helper functions; no registry model.
- `models/authority_helpers.py` — explicit Recruiter / Hiring Manager / Recruitment Manager server guards.
- `models/native_recruitment.py` — Odoo-native extensions for applicant, stage, job and talent pool.
- `models/requisition.py` — ED3 requisition demand/approval lifecycle.
- `models/interview.py` — ED2 interview template plus ED3 session/score evidence.
- `models/offer.py` — ED3 governed offer and soft document integration.
- `models/preboarding.py` — ED3 hire/preboarding orchestration.
- `models/source_metric.py` — ED4 immutable recruitment source/funnel snapshots.

## Custom persistent models

Exactly seven:

1. `onehr.recruitment.requisition`
2. `onehr.interview.template`
3. `onehr.interview.session`
4. `onehr.interview.score`
5. `onehr.offer`
6. `onehr.preboarding`
7. `onehr.recruitment.source.metric`

## Security inventory

- Custom groups: Hiring Manager, Recruiter, Recruitment Manager.
- ACL rows: 21.
- No custom persistent model grants CRUD to `base.group_user`.
- No custom persistent model grants unlink through ACL.
- Global allowed-company record rule exists for every custom persistent model.
- Hiring Manager operational visibility is assigned-record scoped.
- Recruiter operational visibility remains inside allowed companies.
- Compensation fields are separately group-restricted in the offer model/UI.
- Applicant-to-employee conversion is explicitly Recruitment Manager-only when a new employee must be created.

## Data

- Requisition sequence: `onehr.recruitment.requisition`.
- Offer sequence: `onehr.recruitment.offer`.

## Views / actions

Dedicated list/form/search views exist for every custom persistent model. Additional calendar, pivot and graph views are present where the business object benefits from them. Odoo-native applicant/stage/job/talent-pool views are inherited rather than duplicated.

## Tests

Exactly 20 post-install test methods across four test modules, covering registry ownership, requisition lifecycle, approval callback, evidence immutability, interview scoring/correction, offer lifecycle, preboarding gates, multi-company security, and immutable/idempotent source snapshots.

## Deletion/history behavior

All seven custom persistent models use `@api.ondelete(at_uninstall=False)` rather than business `unlink()` overrides. This protects governed history during normal operation while not intentionally blocking module uninstall.

FULL_STRUCTURAL_INVENTORY_RESULT: PASS_SOURCE
RUNTIME_STRUCTURE_RESULT: PENDING

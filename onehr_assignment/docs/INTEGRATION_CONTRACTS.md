
# onehr_assignment — Integration Contracts

## onehr_base

Consumes `onehr.position`, `onehr.grade`, native department/job/work-location extensions and approved mixins. Assignment consumes position capacity; it does not re-own Base masters or silently rewrite the Base position lifecycle status.

## onehr_corehr / Odoo native HR

`hr.employee` remains canonical worker identity. Approved **primary** Assignment synchronizes job, department, work location, OneHR grade and OneHR primary position to an Odoo `hr.version` effective on `effective_from`. Direct manager remains Odoo `hr.employee.parent_id`. Secondary assignments do not overwrite canonical primary employment placement.

## onehr_workflow_approval

Assignment, Movement Request and Workforce Plan use `onehr.mixin.approvable`. The workflow callback executes under the final approver's security context, therefore final approval routes for these source documents must resolve to a user holding the corresponding source authority; Assignment Manager is the intended final execution/approval authority for movements/workforce plans.

## onehr_security

No broad internal-user access. Proposer/Officer/Manager roles are explicit and company/direct-report scoped. `onehr.audit.log` remains owned by Security. No security-model source is modified here.

## onehr_employment_contract — no hard dependency

Legal contract state and contract evidence remain Contract-owned. Assignment may consume common native `hr.version` facts but does not reference Contract models directly, avoiding reverse/circular dependency.

## onehr_recruitment — no hard dependency

Recruitment owns hire pipeline/preboarding. Assignment remains independently installable after Core HR/Security/Approval. Future hire orchestration can call Assignment through an approved downstream extension without making Recruitment a hard dependency here.

## onehr_multicompany_branch — future/soft extension

Company is the current hard security partition. No `onehr.branch` field/model is invented. Branch narrowing may later extend Assignment through the branch owner's architecture without reversing dependency direction.

## onehr_payroll_bridge / finance — downstream adapters

`onehr.assignment.cost.allocation` stores neutral effective costing dimensions and percentages. It does not own payroll work entries, analytic accounts, GL accounts or payroll posting.

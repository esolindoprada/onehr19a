
# HARD GATE 11 — Database Identifier & ORM Naming Safety

Canonical ORM/table mapping:
- `onehr.policy` → `onehr_policy`
- `onehr.policy.ack` → `onehr_policy_ack`
- `onehr.policy.evidence` → `onehr_policy_evidence`

Explicit Many2many relations:
- `onehr_pnp_policy_compliance_user_rel`
- `onehr_pnp_policy_department_rel`
- `onehr_pnp_policy_job_rel`
- `onehr_pnp_policy_employee_rel`
- `onehr_pnp_policy_attachment_rel`
- `onehr_pnp_evidence_attachment_rel`

Constraint attributes:
- `_policy_code_version_company_uniq`
- `_policy_employee_ack_uniq`

All explicit relation tables/columns and projected identifiers must remain
lowercase snake_case and <=63 UTF-8 bytes.

Source acceptance checks:
- exact model/table names;
- declared field names;
- predicted indexed-field identifiers;
- explicit Many2many relation and column identifiers plus collision detection;
- projected constraint identifiers;
- duplicate local XML IDs;
- forbidden static ORM relations to soft modules;
- forbidden `id`/`.id` in `@api.depends`;
- legacy `_sql_constraints`.

Any truncation/collision/naming ambiguity is a release-blocking source failure.


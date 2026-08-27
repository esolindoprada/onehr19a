# HARD GATE 11 — Database Identifier & ORM Naming Safety

Canonical ORM/table mapping:
- `onehr.sop` → `onehr_sop`
- `onehr.sop.version` → `onehr_sop_version`
- `onehr.sop.ack` → `onehr_sop_ack`

Explicit Many2many relations:
- `onehr_sop_reviewer_rel`
- `onehr_sop_approver_rel`
- `onehr_sop_ver_dept_rel`
- `onehr_sop_ver_job_rel`
- `onehr_sop_ver_emp_rel`
- `onehr_sop_ver_audience_rel`

All are explicit, unique, lowercase snake_case and safely below PostgreSQL's
63-byte identifier ceiling.

Constraint attributes:
- `_sop_code_company_uniq`
- `_sop_version_uniq`
- `_sop_ack_employee_uniq`

Source acceptance checks:
- model/table names;
- every declared field name;
- predicted indexed-field identifiers;
- explicit Many2many relation/column names and collisions;
- constraint projected names;
- duplicate local XML IDs;
- static ORM relations to forbidden soft OneHR models;
- forbidden `id`/`.id` in `@api.depends`;
- legacy `_sql_constraints`.

Identifier truncation/collision ambiguity is a release-blocking source failure.

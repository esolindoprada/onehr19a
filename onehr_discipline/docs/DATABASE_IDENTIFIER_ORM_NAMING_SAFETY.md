# HARD GATE 11 — Database Identifier & ORM Naming Safety

Canonical ORM/table mapping:
- `onehr.discipline.case` → `onehr_discipline_case`
- `onehr.discipline.sanction` → `onehr_discipline_sanction`

Explicit Many2many relations:
- `onehr_disc_case_evidence_rel`
- `onehr_disc_case_hearing_rel`
- `onehr_disc_case_appeal_panel_rel`
- `onehr_disc_case_appeal_rel`
- `onehr_disc_sanction_decision_rel`
- `onehr_disc_sanction_execution_rel`

Constraint attributes:
- `_reference_company_uniq` on both persistent models.

Source acceptance checks:
- exact model/table names;
- lowercase dotted model naming and snake_case fields;
- PostgreSQL 63 UTF-8 byte limit;
- indexed-field identifier projections;
- explicit M2M relation/column lengths and collision detection;
- projected constraint identifier lengths;
- duplicate local XML IDs;
- static ORM relation boundary to soft modules;
- no `id` / `.id` dependency in `@api.depends`;
- no legacy `_sql_constraints`.

Any truncation/collision/ambiguous naming failure blocks runtime.

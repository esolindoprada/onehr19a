
# OneHR Portal Self-Service — Database Identifier & ORM Naming Safety

HARD GATE: 11
TARGET: PostgreSQL / Odoo 19 CE

## Model/table identifiers
- `onehr.portal.request.type` → generated table `onehr_portal_request_type`
- `onehr.portal.request.stage` → generated table `onehr_portal_request_stage`
- `onehr.portal.request` → generated table `onehr_portal_request`
- transient model names are also below PostgreSQL identifier limits.

## Explicit relation identifiers
The principal Portal attachment Many2many deliberately uses the short explicit relation:
- `onehr_port_req_att_rel`

This avoids generated long relation-table names and leaves margin for PostgreSQL's 63-byte
identifier ceiling. Existing canonical Odoo/OneHR relations are not renamed.

## Constraint policy
- Odoo 19 `models.Constraint` is used for SQL uniqueness where required.
- Legacy `_sql_constraints` is forbidden.
- Python constraints are used for company/shared catalogue uniqueness where NULL semantics
  would make a simple SQL unique constraint ambiguous.
- No raw SQL DDL or database trigger is used.

## ORM safety rules
- canonical model names come from the approved Portal product contract;
- no model name is shortened by inventing an alternate business entity;
- Many2one/One2many inverse fields are explicit and stable;
- no relation/column is reused for unrelated business meanings;
- reserved lifecycle/evidence fields are action-controlled rather than externally writable.

DATABASE_IDENTIFIER_ORM_NAMING_SAFETY_SOURCE: PASS_PENDING_RUNTIME_REGISTRY


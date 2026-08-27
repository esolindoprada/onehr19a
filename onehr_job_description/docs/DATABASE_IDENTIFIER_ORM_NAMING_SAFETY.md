# HARD GATE 11 — Database Identifier & ORM Naming Safety

## Approved ORM identities
- model `onehr.jd` → table `onehr_jd`
- model `onehr.jd.version` → table `onehr_jd_version`

Both are deterministic lowercase PostgreSQL identifiers well below 63 bytes.

## Explicit Many2many relation tables
- `onehr_jd_reviewer_rel`
- `onehr_jd_approver_rel`
- `onehr_jd_version_attachment_rel`

Each relation table is unique, lowercase snake_case and <=63 bytes.

## Constraint identifiers
Python constraint attributes are deliberately compact:
- `_jd_code_company_uniq`
- `_jd_position_company_uniq`
- `_jd_version_number_uniq`

The source acceptance tool checks their identifier lengths and the associated table
identity.

## Field and index safety
Source acceptance parses field assignments and checks:
- lowercase snake_case;
- no whitespace/hyphen/uppercase;
- <=63 UTF-8 bytes;
- predicted `<table>_<field>_index` identifier length <=63 for indexed fields;
- no duplicate field declaration within the same class by AST inventory.

## ORM dependency safety
- no static field references to soft modules;
- Career competency access is dynamic through registry lookup;
- no explicit `id` or `.id` in `@api.depends`;
- no legacy `_sql_constraints`;
- no duplicate local XML external ID;
- no public controller model alias.

Any failure blocks `SOURCE_ENTERPRISE_COMPLETENESS`.

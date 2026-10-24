# OneHR Analytics — Provider Matrix

| Provider | Configuration | Output | Drill-through | Security behavior |
|---|---|---|---|---|
| Manual | `manual_value` | numeric value | none | Analytics Manager only for configuration/snapshot |
| Model Aggregate | approved source + Count/Sum/Average + literal domain + optional date field | aggregate + record count | source model/domain | source ACL/rules remain authoritative; company scope appended; branch fails closed |
| Appraisal Service | approved Appraisal metric | numeric KPI service fact | company-scoped Appraisal forms | Appraisal's own authority check remains authoritative |
| Learning Service | approved Learning metric | numeric KPI service fact | company-scoped Learning sessions | Learning's own authority check remains authoritative |
| Career Service | approved Career metric | numeric KPI service fact | company-scoped talent pool | Career's own authority check remains authoritative |

## Formula safety
There is deliberately no free-form Python formula. Configurable filters use only a literal Odoo
domain parsed by `ast.literal_eval`. The provider does not expose arbitrary model names,
arbitrary method names, `eval`, `safe_eval` or business `sudo()`.

## Snapshot trend evidence
Each snapshot can retain current value plus previous-period, month-over-month, half-over-half
and year-over-year baseline/change percentages where matching historical evidence exists.

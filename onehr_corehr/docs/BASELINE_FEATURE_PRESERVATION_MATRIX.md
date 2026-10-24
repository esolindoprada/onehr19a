
# onehr_corehr — Baseline / Feature Preservation Matrix

| Historical intent | Direct Full Build disposition |
|---|---|
| Employee master | PRESERVED_AND_CORRECTED — native `hr.employee + hr.version`, no `onehr.employee` |
| Employee number / identity | PRESERVED — enterprise employee number on native employee |
| Biodata/contact/organization | PRESERVED — native Odoo employee/version fields remain canonical |
| Dependents/family | PRESERVED — `onehr.employee.dependent` ED1 |
| Emergency contact | PRESERVED_AND_EXPANDED — multi-row effective contacts with primary control |
| HR documents / KTP/NPWP/BPJS / expiry | MOVED_WITHOUT_LOSS — owner is `onehr_document`; Core HR does not duplicate it |
| Identifier administration | PRESERVED_AND_HARDENED — masked effective-dated restricted identifier portfolio |
| Education | PRESERVED_AND_EXPANDED — multi-row history; native summary fields remain native |
| Prior employment | PRESERVED — external history only; internal placement reserved for assignment addon |
| Search/filter/completeness | PRESERVED — employee number, engagement/grade/position, profile status/completeness |
| Chatter/activity | PRESERVED — approved OneHR audit mixin on custom history models |
| Import wizard | PRESERVED_BY_NATIVE_CAPABILITY — Odoo Data Import; no unregistered transient wizard |
| Employee card/report | PRESERVED — safe OneHR Employee Profile Summary PDF |
| Employee list by unit/job | PRESERVED — native employee list/search/group-by/export |
| Multi-company | PRESERVED_AND_HARDENED — company record rules; branch narrowing deferred to branch owner |
| Occupational health | ENTERPRISE_EXPANSION — work incident, medical assessment, accommodation with isolated ACL |
| PII-aware security | PRESERVED_AND_HARDENED — dedicated identifier/OH groups and structured security audit |

PRESERVATION_RESULT: PASS_AT_SOURCE_DESIGN

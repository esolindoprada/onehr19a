# OneHR Base — Master Model Registry Alignment

| # | Model | Classification | ED | Implementation |
|---:|---|---|---|---|
| 1 | `hr.department` | INHERIT_ODOO | ED1 | `models/native_models.py` |
| 2 | `hr.job` | INHERIT_ODOO | ED1 | `models/native_models.py` |
| 3 | `hr.work.location` | INHERIT_ODOO | ED1 | `models/native_models.py` |
| 4 | `onehr.job.family` | NEW persistent | ED1 | `models/organization.py` |
| 5 | `onehr.position` | NEW persistent | ED1 | `models/organization.py` |
| 6 | `onehr.position.hierarchy` | NEW persistent | ED0 | `models/hierarchy.py` |
| 7 | `onehr.position.hierarchy.version` | NEW persistent | ED2 | `models/hierarchy.py` |
| 8 | `onehr.position.hierarchy.node` | NEW persistent | ED2 | `models/hierarchy.py` |
| 9 | `onehr.grade` | NEW persistent | ED1 | `models/organization.py` |
| 10 | `onehr.grade.step` | NEW persistent | ED1 | `models/organization.py` |
| 11 | `onehr.sequence.rule` | NEW persistent | ED1 | `models/configuration.py` |
| 12 | `onehr.eligibility.profile` | NEW persistent | ED1 | `models/configuration.py` |
| 13 | `onehr.lifecycle.event.type` | NEW persistent | ED0 | `models/configuration.py` |
| 14 | `onehr.checklist.template` | NEW persistent | ED2 | `models/checklist.py` |
| 15 | `onehr.checklist.task.template` | NEW persistent | ED2 | `models/checklist.py` |
| 16 | `onehr.checklist.instance` | NEW persistent | ED3 | `models/checklist.py` |
| 17 | `onehr.checklist.task` | NEW persistent | ED3 | `models/checklist.py` |
| 18 | `onehr.mixin.audit` | NEW abstract | ED0 | `models/mixins.py` |
| 19 | `onehr.mixin.effective.dated` | NEW abstract | ED0 | `models/mixins.py` |

## DO NOT CREATE

- `onehr.org.unit`
- `onehr.job`
- `onehr.location`
- `onehr.employee`

## Dependency Contract

Hard dependencies remain exactly `hr`, `mail`.

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS
RUNTIME_REGISTRY_RESULT: PENDING

# onehr_employment_contract — Model Registry Alignment

| Model | Classification | Effective Dating / Evidence | Ownership |
|---|---|---|---|
| `onehr.contract.template` | NEW persistent | ED2 versioned policy | Employment Contract |
| `onehr.contract` | NEW persistent | ED3 legal/workflow evidence | Employment Contract |
| `hr.version` | Odoo-native reference only | Odoo native temporal employment version | Odoo/CoreHR |

## DO NOT CREATE
- `onehr.employee`
- `onehr.hr.version`
- a parallel canonical employment-contract facts model
- a second grade/position/job/department master

`onehr.contract` references `hr.version` and exposes non-stored live related fields.
Frozen `snapshot_*` fields are approval/legal evidence only; they are not a mutable
second source of employment truth.

Hard dependencies remain exactly:
`onehr_corehr`, `onehr_security`, `onehr_workflow_approval`.

REGISTRY_ALIGNMENT_SOURCE_RESULT: PASS
RUNTIME_REGISTRY_RESULT: PENDING

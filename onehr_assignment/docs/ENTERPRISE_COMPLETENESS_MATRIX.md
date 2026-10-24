
# onehr_assignment — Enterprise Completeness Matrix

| Area | Source status | Windows runtime status | Evidence / acceptance |
|---|---|---|---|
| Project identity / exact addon | PASS | PENDING | Manifest + preflight |
| Exact 7 Registry-owned persistent models | PASS | PENDING | Registry alignment + source acceptance |
| Hard dependencies exact | PASS | PENDING | Manifest |
| Native employee/hr.version ownership preserved | PASS | PENDING | Primary sync contract |
| Primary / secondary placement | PASS | PENDING | Model + runtime tests |
| Effective dating / historical immutability | PASS | PENDING | constraints + ondelete + state guards |
| One primary overlap rule | PASS | PENDING | assignment validation/tests |
| Employee FTE <= 1 | PASS | PENDING | assignment validation/tests |
| Position HC/FTE capacity | PASS | PENDING | capacity engine/tests |
| Effective position-budget override | PASS | PENDING | position budget engine/tests |
| Movement request / batch lines | PASS | PENDING | ED3 persistent request/line + tests |
| Future movement / scheduled activation | PASS | PENDING | successor + daily scheduler |
| Assignment cost allocation 100% | PASS | PENDING | effective coverage engine/tests |
| Workforce plan versioning | PASS | PENDING | plan/version actions/tests |
| Position budget materialization | PASS | PENDING | plan activation/tests |
| Workflow approval integration | PASS | PENDING | approvable hooks; runtime matrix required |
| Least-privilege security | PASS | PENDING | ACL/rules/field groups/tests |
| List/Form/Search every custom model | PASS | PENDING | source acceptance; Odoo view validation pending |
| Advanced enterprise UI | PASS | PENDING | statusbar/smart/body/O2M/chatter |
| Report / analytics | PASS | PENDING | QWeb + Calendar/Pivot/Graph |
| Fresh install | NOT_RUN | PENDING | Windows Odoo 19 |
| Upgrade and repeat upgrade | NOT_RUN | PENDING | Windows Odoo 19 |
| 26 runtime tests | SOURCE_READY | PENDING | `--test-tags /onehr_assignment` |
| Uninstall/reinstall safety on disposable DB | NOT_RUN | PENDING | Windows Odoo 19 |
| Cross-addon regression | NOT_RUN | PENDING | OneHR installed suite |

SOURCE_ENTERPRISE_COMPLETENESS: PASS_FOR_RUNTIME
WINDOWS_RUNTIME_ACCEPTANCE: PENDING
ONEHR_ASSIGNMENT_MOVE_FORWARD_READY: NO

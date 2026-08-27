# OneHR Recruitment — Enterprise Completeness Matrix

| Domain | Source status | Runtime status | Acceptance note |
|---|---|---|---|
| Project identity / dependencies | PASS | PENDING | exact addon/dependency contract |
| Registry/native-first ownership | PASS | PENDING | 11 approved rows; no parallel applicant/stage/job/talent-pool master |
| Requisition demand governance | PASS | PENDING | draft/approval/recruiting/filled/cancelled; submitted demand frozen |
| Workflow Approval integration | PASS | PENDING | requisition and offer use `onehr.mixin.approvable`; source retains state ownership |
| Applicant pipeline integration | PASS | PENDING | extends native `hr.applicant`; no duplicate applicant |
| Interview template versioning | PASS | PENDING | ED2 active/effective non-overlap; published definition immutable |
| Interview scheduling/evidence | PASS | PENDING | calendar link, assigned interviewers, frozen template identity, finalized scores |
| Score correction/history | PASS | PENDING | final evidence immutable; correction supersedes rather than rewrites |
| Offer governance | PASS | PENDING | compensation, approval, send/response/expiry lifecycle; accepted offer gates preboarding |
| OneHR Document soft integration | PASS | PENDING | offer opens governed document generation only when installed/configured |
| Native employee conversion | PASS | PENDING | uses Odoo native applicant conversion; creating employee is Recruitment Manager-only |
| Preboarding / HIRE checklist | PASS | PENDING | generic base checklist allocated; downstream owners remain extension hooks |
| Recruitment analytics snapshot | PASS | PENDING | ED4 immutable/idempotent source funnel snapshot |
| Multi-company isolation | PASS | PENDING | global allowed-company rules on every custom persistent model |
| Branch architecture compatibility | PASS | PENDING | no reverse dependency; branch owner may extend later |
| Security / separation of duties | PASS | PENDING | three role levels; no broad custom-model base user ACL; no source sudo bypass |
| Professional UI/UX | PASS | PENDING | list/form/search every custom persistent model; advanced business buttons/views |
| Automated tests | PASS structural | PENDING execution | 20 post-install tests; runtime execution required |
| Fresh install | NOT RUN | PENDING | Windows/Odoo runtime required |
| Upgrade / repeat upgrade | NOT RUN | PENDING | Windows/Odoo runtime required |
| Uninstall / reinstall safety | NOT RUN | PENDING | protected by uninstall-safe ondelete design; runtime proof required |
| Post-upgrade smoke | NOT RUN | PENDING | required before freeze |
| Sibling-addon preservation | PASS package scope | PENDING deployment | deploy helper fingerprints siblings |

SOURCE_ENTERPRISE_COMPLETENESS_REVIEW: PASS_WITH_RUNTIME_PENDING
ONEHR_RECRUITMENT_MOVE_FORWARD_READY: NO

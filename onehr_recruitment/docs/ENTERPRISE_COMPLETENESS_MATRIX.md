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
| Interview score Properties definition | PASS repaired 19.0.1.0.1 | PENDING re-activation | Odoo 19 requires exactly one relation hop; uses `template_id.scorecard_definition` |
| Score correction/history | PASS | PENDING | final evidence immutable; correction supersedes rather than rewrites |
| Offer governance | PASS | PENDING | compensation, approval, send/response/expiry lifecycle; accepted offer gates preboarding |
| OneHR Document soft integration | PASS | PENDING | offer opens governed document generation only when installed/configured |
| Native employee conversion | PASS | PENDING | uses Odoo native applicant conversion; creating employee is Recruitment Manager-only |
| Preboarding / HIRE checklist | PASS | PENDING | generic base checklist allocated; downstream owners remain extension hooks |
| Preboarding pending-task search domain | PASS repaired 19.0.1.0.2 | PENDING re-activation | filter uses searchable `checklist_instance_id.task_ids.state = pending`; no stored duplicate counter introduced |
| Applicant latest-offer search domain | PASS repaired 19.0.1.0.3 | PENDING re-activation | `onehr_latest_offer_state` remains the latest-offer business fact and is now stored/indexed/searchable; offer-state dependency added |
| Job open-requisition search domain | PASS repaired 19.0.1.0.3 | PENDING re-activation | filter uses searchable `onehr_requisition_ids.state in (approved, recruiting)`; display counter remains non-stored |
| Generic Recruitment search-domain compatibility gate | PASS source | PENDING Odoo view validation | all 22 Recruitment view-domain attributes / 27 leaves audited; no target-local non-searchable domain leaf remains |
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

# OneHR Appraisal — Security & Privacy Matrix

| Role | Cycle | Form | Score | Scope |
|---|---|---|---|---|
| Appraisal Participant | Read | Limited write | Limited own/peer rating write | Own appraisal / peer assignment |
| Appraisal Manager | Read | Limited manager write | Manager/team rating + IDP write | Assigned team |
| Appraisal HR Officer | Create/read/write | Create/read/write | Create/read/write | Allowed companies |
| Appraisal HR Manager | Full | Full | Full | Allowed companies |

Security design:
- global company rule applies to all three business models
- participant/manager rules narrow normal record scope
- HR rule restores company-wide HR scope for dual-role users while global company rule remains authoritative
- model `write()`/`create()` methods protect lifecycle and rater ownership
- submitted ratings are locked for normal raters
- no custom Appraisal CRUD for `base.group_user`
- no business `sudo()`
- no public Appraisal controller
- Appraisal result contracts do not expose restricted CoreHR identifier/medical/disability payload


Peer-review privacy boundary:
- peer reviewer assignment and peer-line generation are Appraisal HR governed;
- an assigned peer receives only their assigned `onehr.appraisal.score` evidence rows;
- a peer does not gain read access to another employee's full Appraisal Form;
- employee/manager/reviewer names use stored safe-display snapshots while raw `hr.employee`
  references remain HR-restricted in the UI/model where applicable.

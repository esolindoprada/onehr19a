
# OneHR PnP — Security & Privacy Matrix

| Role | Policy | Acknowledgement | Evidence | Upstream authority |
|---|---|---|---|---|
| Policy Reader | assigned Published/Review/Archived read | own assignment | own employee evidence | OneHR Security user |
| Policy Owner | own versions create/read/write under lifecycle guards | own-reader view only | own-reader evidence | Approval User + Document User |
| Compliance Officer | company policy working set; publish/review | company register | company evidence verify/reject + unit/policy-wide evidence | Workflow Approver + Document Manager + HR User |
| PnP Administrator | PnP administrative source authority | retained history | retained history | does not automatically gain Workflow Manager, Security Admin or Document Compliance |

Controls:
- global allowed-company rule on all three PnP models;
- Reader visibility derives from generated employee publication assignment;
- Owner gets own policy versions, not company-wide employee evidence;
- Compliance gets company scope required for audience resolution;
- Workflow routing eligibility remains controlled by OneHR Workflow Approval rules;
- restricted OneHR Document categories still require explicit Document Compliance;
- acknowledgement lifecycle cannot be written directly;
- acknowledgement rows cannot be deleted;
- employee evidence is own-assignment only;
- unit/policy-wide evidence requires Compliance;
- submitted/verified evidence content is immutable and non-Draft evidence retained;
- no custom `base.group_user` CRUD;
- no business `.sudo()`;
- no public controller.


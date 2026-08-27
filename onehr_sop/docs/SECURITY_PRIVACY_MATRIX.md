# OneHR SOP — Security & Privacy Matrix

| Role | SOP | Version | Ack | Scope |
|---|---|---|---|---|
| SOP Reader | current assigned SOP read | current assigned Published version read | own read/write-through-action | allowed company + generated audience evidence |
| SOP QA / Editor | company create/read/write | Draft create/read/write/delete; history read | company read | allowed companies |
| SOP Compliance / Approver | editor rights | approve/publish/obsolete | generated evidence create/read | company + optional assigned approver matrix |
| SOP Administrator | governed admin | governed admin | retained evidence | allowed companies |

Controls:
- global company rules on all three business models;
- Reader visibility derives from generated acknowledgement audience evidence;
- Reader cannot see Draft/Review/Approved or another employee's acknowledgement; Reader may reopen only Published/Obsolete versions for which their own historical acknowledgement assignment exists;
- Editor has workforce-read and Document Officer authority needed for audience resolution/archive work;
- Approver adds Document Manager authority for immutable archive issuance;
- published/obsolete content is locked;
- acknowledgement state cannot be written directly;
- acknowledgement evidence cannot be deleted;
- no custom broad `base.group_user` ACL;
- no business `.sudo()`;
- no public controller.

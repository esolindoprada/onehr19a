# OneHR Job Description — Security & Privacy Matrix

| Role | JD Master | JD Version | Workflow | Scope |
|---|---|---|---|---|
| JD Reader | read current published master | read current published version | none | allowed companies |
| JD HRBP / Comp&Ben Editor | create/read/write, no delete | create/read/write Draft, no delete | submit Review | allowed companies |
| JD Approver | editor rights | editor rights | return, approve, publish | allowed companies + optional assigned approver matrix |
| JD Administrator | governed full CRUD | governed full CRUD | all approval authority | allowed companies |

Security controls:
- global company rules on both models;
- Reader rule exposes only current published evidence;
- Editor rule restores company working set while global company isolation stays active;
- ordinary `base.group_user` receives no custom JD ACL;
- JD Editor/Approver receive the Base position/job-family access needed through
  `hr.group_hr_user` / `hr.group_hr_manager`;
- published identity and submitted/published content are server-side locked;
- approved/published history is retained;
- source documents/change-control evidence are editor-restricted;
- approval routing is enforced in Python when assigned approvers are configured;
- no business `sudo()`;
- no public controller.

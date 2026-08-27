# OneHR Career & Succession — Security & Privacy Matrix

| Role | Competency | Position Competency | Talent Pool | Succession Plan | Scope |
|---|---|---|---|---|---|
| HRBP | CRUD except delete | CRUD except delete | create/read/write, governed workflow start | create/read/write, propose | allowed companies |
| Talent Manager | governed full CRUD | governed full CRUD | approve/activate/deactivate/delete only where allowed | approve/activate/close/cancel | allowed companies |
| Ordinary internal user | none | none | none | none | none |

Controls:
- global company rule on all four persistent models;
- no custom `base.group_user` CRUD;
- no business `sudo()`;
- raw employee references remain HRBP-only in UI where appropriate;
- lifecycle state transitions are action-controlled;
- approved/active historical talent/succession evidence cannot be casually deleted;
- soft Appraisal/Learning integration operates under the caller's source-addon authority;
- UI visibility is never treated as the security boundary.

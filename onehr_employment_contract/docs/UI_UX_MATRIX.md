# onehr_employment_contract — Enterprise UI/UX Matrix

| Model | List | Form | Search | Statusbar | Smart Buttons | Header Actions | Body Actions | One2many Row Actions | Reporting | Chatter |
|---|---|---|---|---|---|---|---|---|---|---|
| `onehr.contract.template` | yes | yes | yes | Draft/Active/Retired | Contracts | Activate, Retire, New Version | policy tabs | N/A | list/search | yes |
| `onehr.contract` | yes | yes | yes | Draft→Review→Approved→Active→Expired/Terminated (+Rejected) | Employee, HR Version, Approvals, Successors, Documents, Clearance | Submit, Reset, Activate, Renewal, Termination Approval/Execution | Generate Document, Request E-Signature, Schedule Expiry, Schedule Clearance | Done/Schedule/Open Checklist | Calendar, Pivot, Graph, expiry/termination actions | yes |

Security remains server-side. Button visibility is only a usability layer.

# Baseline Feature Preservation Matrix

| Historical / approved intent | Direct Full Build implementation | Status |
|---|---|---|
| Multi-company + branch separation | `res.company` remains outer partition; `onehr.branch` is inner operational scope | PRESERVED / HARDENED |
| Branch master | Effective-dated `onehr.branch` with hierarchy, type, manager, lifecycle and audit | PRESERVED / EXPANDED |
| Default branch per user | `res.users.onehr_default_branch_id` plus controlled quick-selector action | PRESERVED |
| Allowed branches per user | Explicit `onehr_allowed_branch_ids` intersected with Odoo allowed companies | PRESERVED / HARDENED |
| Central office visibility | `group_onehr_central_office` reads only explicitly allowed branches and consolidated role coverage | PRESERVED / HARDENED |
| Branch user / manager / admin roles | Odoo 19 `res.groups.privilege` groups with least privilege | PRESERVED / HARDENED |
| Branch record rules | Legal-company global rule + explicit allowed-branch group rule | PRESERVED / HARDENED |
| Quick branch selector | Safe `Set as My Default Branch` action on branch list/form; no unnecessary JS dependency | PRESERVED, IMPLEMENTATION MODERNIZED |
| Branch mixin | Registry-approved abstract `onehr.mixin.branch` | PRESERVED / CANONICALIZED |
| Security integration | `onehr.user.role.branch_id`, overlap/SoD hooks and branch-aware group reconciliation | ENTERPRISE INTEGRATED |
| Consolidated reporting | Pivot/graph over security-owned `onehr.user.role`; no unregistered reporting model | PRESERVED / HARDENED |
| Odoo 18 scaffold metadata | Replaced with Odoo 19 CE manifest/views/security | REQUIRED TECHNICAL RECONSTRUCTION |
| Generic scaffold model | Rejected because absent from Registry; `onehr.branch` is canonical | REJECTED WITH ARCHITECTURE REASON |
| broad `base.group_user` CRUD | Removed | SECURITY HARDENING |

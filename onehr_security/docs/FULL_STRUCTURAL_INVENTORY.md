
# OneHR Security — Full Structural Inventory

Generated from the final Direct Full Build source.

## `onehr.audit.log`

- Python class: `OneHRAuditLog`
- Classification: NEW persistent
- Effective dating: ED3
- Source: `models/audit.py`
- Fields declared here: `event_at`, `actor_user_id`, `company_id`, `action`, `severity`, `model_name`, `res_id`, `summary`, `changed_fields`, `before_json`, `after_json`, `metadata_json`, `correlation_id`, `role_id`, `user_role_id`, `is_anonymized`, `anonymized_at`, `anonymized_by_id`
- Methods/actions declared here: `_json_dump`, `_log_event`, `write`, `_unlink_except_module_uninstall`, `action_anonymize_payload`, `action_open_target`

## `res.users`

- Python class: `ResUsers`
- Classification: INHERIT_ODOO
- Effective dating: ED0
- Source: `models/res_users.py`
- Fields declared here: `onehr_role_assignment_ids`, `onehr_effective_role_ids`, `onehr_role_assignment_count`, `onehr_effective_role_count`, `onehr_sod_conflict_count`, `onehr_audit_event_count`, `onehr_last_access_reconciled_at`, `onehr_security_note`
- Methods/actions declared here: `_compute_onehr_security_summary`, `_search_onehr_effective_role_ids`, `_search_onehr_sod_conflict_count`, `create`, `write`, `_onehr_branch_scope_assignment_domain`, `_onehr_managed_group_ids`, `_onehr_desired_group_ids`, `_reconcile_onehr_groups`, `action_reconcile_onehr_access`, `action_open_onehr_role_assignments`, `action_open_onehr_sod_conflicts`, `action_open_onehr_audit_events`

## `onehr.role`

- Python class: `OneHRRole`
- Classification: NEW persistent
- Effective dating: ED1
- Source: `models/role.py`
- Fields declared here: `code`, `name`, `sequence`, `description`, `company_id`, `active`, `sensitivity`, `group_ids`, `assignment_ids`, `sod_rule_a_ids`, `sod_rule_b_ids`, `assignment_count`, `active_user_count`, `sod_rule_count`
- Methods/actions declared here: `_check_group_mapping_authority`, `_check_protected_group_mapping`, `create`, `write`, `_check_unique_code_scope`, `_compute_counts`, `action_open_assignments`, `action_open_effective_users`, `action_open_sod_rules`, `action_reconcile_assigned_users`, `_unlink_except_module_uninstall`

## `onehr.sod.matrix`

- Python class: `OneHRSodMatrix`
- Classification: NEW persistent
- Effective dating: ED1
- Source: `models/sod.py`
- Fields declared here: `code`, `name`, `company_id`, `active`, `role_a_id`, `role_b_id`, `severity`, `enforcement`, `mitigation_guidance`, `conflict_count`
- Methods/actions declared here: `create`, `write`, `_check_distinct_roles`, `_check_no_symmetric_overlap`, `applies_to_company`, `conflicts_with_roles`, `_compute_conflict_count`, `action_open_conflicts`, `_unlink_except_module_uninstall`, `action_scan_effective_assignments`

## `onehr.sod.conflict.log`

- Python class: `OneHRSodConflictLog`
- Classification: NEW persistent
- Effective dating: ED3
- Source: `models/sod.py`
- Fields declared here: `detected_at`, `user_id`, `company_id`, `matrix_id`, `user_role_id`, `conflicting_user_role_id`, `severity`, `enforcement`, `details`, `mitigation_guidance`, `state`, `resolution_comment`, `resolved_at`, `resolved_by_id`, `resolution_note`
- Methods/actions declared here: `_record_conflict`, `_resolve`, `action_accept_risk`, `action_mark_mitigated`, `action_resolve`, `write`, `_unlink_except_module_uninstall`, `action_open_user`, `action_open_matrix`

## `onehr.user.role`

- Python class: `OneHRUserRole`
- Classification: NEW persistent
- Effective dating: ED1
- Source: `models/user_role.py`
- Fields declared here: `user_id`, `role_id`, `company_id`, `state`, `effective_status`, `assignment_reason`, `activated_at`, `activated_by_id`, `revoked_at`, `revoked_by_id`, `revocation_reason`, `conflict_count`
- Methods/actions declared here: `_branch_scope_overlap_domain`, `_branch_scope_label`, `create`, `_check_scope_integrity`, `_check_active_overlap`, `write`, `_compute_effective_status`, `_is_effective_today`, `_effective_peer_assignments`, `_applicable_sod_conflicts`, `_find_conflicting_assignment`, `_compute_conflict_count`, `action_activate`, `action_recheck_sod`, `action_revoke`, `action_open_user`, `action_open_role`, `_unlink_only_draft_assignments`, `_cron_reconcile_current_access`

## Module helpers — `models/action_helpers.py`

- `open_records_action`
- `open_record_action`
- `require_security_manager`
- `require_security_admin_or_compliance`

## Module Lifecycle Hook

- `uninstall_hook(env)` in `__init__.py` revokes direct user membership in every Odoo group managed by OneHR role mappings before uninstall removes module structures.
- Groups never mapped by OneHR remain untouched by that cleanup.

## Security Objects

- Odoo 19 `res.groups.privilege` for OneHR Security.
- Security User, Security Manager, Security Admin, Compliance Officer.
- Sensitive Data Reader and Restricted Data Reader explicit access gates.
- 18 ACL rows.
- Company/self record rules covering role, user-role, SoD evidence, audit, and OneHR security management of native users.
- Daily root cron for effective-role reconciliation.

## View Coverage

- `onehr.role`: list/form/search.
- `onehr.user.role`: list/form/search.
- `onehr.sod.matrix`: list/form/search.
- `onehr.sod.conflict.log`: list/form/search.
- `onehr.audit.log`: list/form/search.
- `res.users`: native Odoo list/form/search extended by OneHR Security.


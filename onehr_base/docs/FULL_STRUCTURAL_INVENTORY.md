

# OneHR Base — Full Structural Inventory

Generated from the Direct Full Build source. Fields inherited through approved Odoo mixins/native models are noted by model ownership rather than duplicated here.

## `onehr.checklist.template`

- Python class: `OneHRChecklistTemplate`
- Classification: NEW persistent
- Effective Dating: ED2
- Source owner: `models/checklist.py`
- Fields declared here: `code`, `name`, `version`, `lifecycle_event_type_id`, `eligibility_profile_id`, `company_id`, `state`, `task_template_ids`, `task_template_count`, `instance_count`
- Methods declared here: `_check_unique_version`, `_check_active_overlap`, `_compute_task_template_count`, `_compute_instance_count`, `action_activate`, `action_retire`, `action_create_new_version`, `action_open_task_templates`, `action_open_instances`

## `onehr.checklist.task.template`

- Python class: `OneHRChecklistTaskTemplate`
- Classification: NEW persistent
- Effective Dating: ED2
- Source owner: `models/checklist.py`
- Fields declared here: `template_id`, `company_id`, `sequence`, `name`, `instructions`, `due_offset_days`, `evidence_required`, `performer_policy`, `performer_user_id`, `dependency_ids`
- Methods declared here: `_check_performer`, `_check_dependencies`, `resolve_performer`, `action_open_template`

## `onehr.checklist.instance`

- Python class: `OneHRChecklistInstance`
- Classification: NEW persistent
- Effective Dating: ED3
- Source owner: `models/checklist.py`
- Fields declared here: `name`, `employee_id`, `company_id`, `lifecycle_event_type_id`, `template_id`, `template_code`, `template_name`, `template_version`, `event_date`, `source_model`, `source_res_id`, `state`, `task_ids`, `completed_at`, `completed_by_id`, `task_count`, `pending_task_count`, `completed_task_count`
- Methods declared here: `_onchange_template_id`, `_check_source_reference_pair`, `create`, `build_eligibility_context`, `_allocation_context`, `_allocate_frozen_tasks`, `_compute_task_counts`, `action_complete`, `action_cancel`, `action_schedule_outstanding_activities`, `action_open_tasks`, `write`, `_unlink_except_completed_history`

## `onehr.checklist.task`

- Python class: `OneHRChecklistTask`
- Classification: NEW persistent
- Effective Dating: ED3
- Source owner: `models/checklist.py`
- Fields declared here: `instance_id`, `company_id`, `employee_id`, `source_task_template_id`, `sequence`, `name`, `instructions`, `due_date`, `evidence_required`, `performer_policy`, `assigned_user_id`, `dependency_ids`, `activity_id`, `state`, `completed_at`, `completed_by_id`, `completion_note`, `evidence_attachment_ids`
- Methods declared here: `action_done`, `action_cancel`, `action_schedule_activity`, `action_open_instance`, `write`, `_unlink_except_completed_evidence`

## `onehr.sequence.rule`

- Python class: `OneHRSequenceRule`
- Classification: NEW persistent
- Effective Dating: ED1
- Source owner: `models/configuration.py`
- Fields declared here: `code`, `name`, `purpose`, `company_id`, `sequence_id`, `active`
- Methods declared here: `_check_rule_overlap`, `_check_sequence_company`, `next_value`

## `onehr.eligibility.profile`

- Python class: `OneHREligibilityProfile`
- Classification: NEW persistent
- Effective Dating: ED1
- Source owner: `models/configuration.py`
- Fields declared here: `code`, `name`, `company_id`, `active`, `department_ids`, `job_ids`, `position_ids`, `grade_ids`, `work_location_ids`, `classification_keys`, `min_service_months`, `max_service_months`
- Methods declared here: `_check_service_range`, `matches`

## `onehr.lifecycle.event.type`

- Python class: `OneHRLifecycleEventType`
- Classification: NEW persistent
- Effective Dating: ED0
- Source owner: `models/configuration.py`
- Fields declared here: `code`, `name`, `sequence`, `active`, `checklist_template_count`
- Methods declared here: `_check_unique_code`, `create`, `write`, `_compute_checklist_template_count`, `action_open_checklist_templates`

## `onehr.position.hierarchy`

- Python class: `OneHRPositionHierarchy`
- Classification: NEW persistent
- Effective Dating: ED0
- Source owner: `models/hierarchy.py`
- Fields declared here: `name`, `code`, `purpose`, `company_id`, `active`, `version_ids`, `version_count`
- Methods declared here: `_check_unique_code`, `_compute_version_count`, `action_open_versions`

## `onehr.position.hierarchy.version`

- Python class: `OneHRPositionHierarchyVersion`
- Classification: NEW persistent
- Effective Dating: ED2
- Source owner: `models/hierarchy.py`
- Fields declared here: `hierarchy_id`, `version`, `name`, `company_id`, `state`, `node_ids`, `node_count`
- Methods declared here: `_compute_name`, `_check_unique_version`, `_check_active_overlap`, `_compute_node_count`, `action_activate`, `action_retire`, `action_open_nodes`

## `onehr.position.hierarchy.node`

- Python class: `OneHRPositionHierarchyNode`
- Classification: NEW persistent
- Effective Dating: ED2
- Source owner: `models/hierarchy.py`
- Fields declared here: `version_id`, `company_id`, `position_id`, `parent_id`, `parent_path`, `child_ids`, `sequence`
- Methods declared here: `_check_unique_position`, `_check_parent_version_and_cycle`, `action_open_position`

## `onehr.mixin.audit`

- Python class: `OneHRAuditMixin`
- Classification: NEW abstract
- Effective Dating: ED0
- Source owner: `models/mixins.py`
- Fields declared here: None (inherited/behavior-only)
- Methods declared here: `log_business_action`

## `onehr.mixin.effective.dated`

- Python class: `OneHREffectiveDatedMixin`
- Classification: NEW abstract
- Effective Dating: ED0
- Source owner: `models/mixins.py`
- Fields declared here: `valid_from`, `valid_to`
- Methods declared here: `_check_valid_interval`, `is_effective_on`, `effective_domain`, `_overlap_domain`, `_check_no_effective_overlap`

## `hr.department`

- Python class: `HrDepartment`
- Classification: INHERIT_ODOO
- Effective Dating: ED1
- Source owner: `models/native_models.py`
- Fields declared here: `onehr_code`, `onehr_unit_type`, `onehr_valid_from`, `onehr_valid_to`, `onehr_position_count`
- Methods declared here: `onehr_is_effective_on`, `onehr_effective_domain`, `_check_onehr_valid_interval`, `_compute_onehr_position_count`, `action_open_onehr_positions`

## `hr.job`

- Python class: `HrJob`
- Classification: INHERIT_ODOO
- Effective Dating: ED1
- Source owner: `models/native_models.py`
- Fields declared here: `onehr_code`, `onehr_job_family_id`, `onehr_grade_ids`, `onehr_valid_from`, `onehr_valid_to`, `onehr_position_count`
- Methods declared here: `onehr_is_effective_on`, `onehr_effective_domain`, `_check_onehr_valid_interval`, `_compute_onehr_position_count`, `action_open_onehr_positions`

## `hr.work.location`

- Python class: `HrWorkLocation`
- Classification: INHERIT_ODOO
- Effective Dating: ED1
- Source owner: `models/native_models.py`
- Fields declared here: `onehr_site_code`, `onehr_timezone`, `onehr_latitude`, `onehr_longitude`, `onehr_business_metadata`, `onehr_valid_from`, `onehr_valid_to`, `onehr_position_count`
- Methods declared here: `onehr_is_effective_on`, `onehr_effective_domain`, `_check_onehr_valid_interval`, `_check_coordinates`, `_compute_onehr_position_count`, `action_open_onehr_positions`

## `onehr.job.family`

- Python class: `OneHRJobFamily`
- Classification: NEW persistent
- Effective Dating: ED1
- Source owner: `models/organization.py`
- Fields declared here: `code`, `name`, `description`, `company_id`, `active`, `position_count`
- Methods declared here: `_validate_scoped_code`, `_check_unique_code`, `_compute_position_count`, `action_open_positions`

## `onehr.grade`

- Python class: `OneHRGrade`
- Classification: NEW persistent
- Effective Dating: ED1
- Source owner: `models/organization.py`
- Fields declared here: `code`, `name`, `sequence`, `description`, `company_id`, `active`, `step_ids`, `position_count`, `step_count`
- Methods declared here: `_validate_scoped_code`, `_check_unique_code`, `_compute_position_count`, `_compute_step_count`, `action_open_positions`, `action_open_steps`

## `onehr.grade.step`

- Python class: `OneHRGradeStep`
- Classification: NEW persistent
- Effective Dating: ED1
- Source owner: `models/organization.py`
- Fields declared here: `grade_id`, `code`, `name`, `sequence`, `company_id`, `active`
- Methods declared here: `_check_unique_grade_code`

## `onehr.position`

- Python class: `OneHRPosition`
- Classification: NEW persistent
- Effective Dating: ED1
- Source owner: `models/organization.py`
- Fields declared here: `code`, `name`, `company_id`, `job_id`, `department_id`, `grade_id`, `work_location_id`, `authorized_fte`, `authorized_headcount`, `status`, `active`, `hierarchy_node_count`
- Methods declared here: `_check_unique_code`, `_check_capacity`, `_check_company_and_temporal_integrity`, `_compute_hierarchy_node_count`, `action_open_hierarchy_nodes`

## Module Helpers — `models/action_helpers.py`

- `open_records_action`
- `open_record_action`

## Module Helpers — `models/native_models.py`

- `_onehr_is_effective_on`
- `_onehr_effective_domain`
- `_check_onehr_valid_interval`

## Module Helpers — `models/organization.py`

- `_validate_scoped_code`

# onehr_corehr — Full Structural Inventory

## `hr.employee`

- Class: `HrEmployee`
- Registry: INHERIT_ODOO / ED2
- Source: `models/employee.py`
- Fields declared here: `onehr_employee_number`, `onehr_profile_completeness`, `onehr_profile_status`, `onehr_engagement_type_id`, `onehr_grade_id`, `onehr_primary_position_id`, `onehr_dependent_ids`, `onehr_emergency_contact_ids`, `onehr_identifier_ids`, `onehr_education_ids`, `onehr_employment_history_ids`, `onehr_dependent_count`, `onehr_emergency_contact_count`, `onehr_identifier_count`, `onehr_education_count`, `onehr_employment_history_count`, `onehr_checklist_count`, `onehr_work_incident_count`, `onehr_medical_assessment_count`, `onehr_disability_record_count`, `onehr_accommodation_required`
- Methods/actions: `create`, `_compute_onehr_profile_completeness`, `_compute_onehr_counts`, `_compute_onehr_identifier_count`, `_compute_onehr_restricted_counts`, `_compute_onehr_accommodation_required`, `_open_employee_children`, `action_open_onehr_dependents`, `action_open_onehr_emergency_contacts`, `action_open_onehr_identifiers`, `action_open_onehr_education`, `action_open_onehr_employment_history`, `action_open_onehr_checklists`, `action_open_onehr_work_incidents`, `action_open_onehr_medical_assessments`, `action_open_onehr_disability_records`

## `hr.employee.public`

- Class: `HrEmployeePublic`
- Registry: INHERIT_ODOO / ED0
- Source: `models/employee.py`
- Fields declared here: `onehr_employee_number`
- Methods/actions: None

## `hr.version`

- Class: `HrVersion`
- Registry: INHERIT_ODOO / ED2
- Source: `models/employee.py`
- Fields declared here: `onehr_engagement_type_id`, `onehr_grade_id`, `onehr_primary_position_id`
- Methods/actions: `_check_onehr_versioned_reference_integrity`

## `onehr.engagement.type`

- Class: `OneHREngagementType`
- Registry: NEW persistent / ED1
- Source: `models/engagement.py`
- Fields declared here: `code`, `name`, `sequence`, `company_id`, `active`, `native_employee_type`, `description`, `version_count`
- Methods/actions: `create`, `write`, `_check_unique_code_scope`, `_check_no_active_overlap`, `_compute_version_count`, `action_open_versions`, `action_archive`, `_unlink_except_module_uninstall`

## `onehr.employee.identifier`

- Class: `OneHREmployeeIdentifier`
- Registry: NEW persistent / ED1
- Source: `models/identifier.py`
- Fields declared here: `reference`, `employee_id`, `company_id`, `identifier_type`, `issuer`, `country_id`, `identifier_value`, `masked_value`, `value_fingerprint`, `verified`, `verified_at`, `verified_by_id`, `active`, `notes`
- Methods/actions: `create`, `write`, `read`, `_compute_masked_value`, `_compute_value_fingerprint`, `_mask_visible_chars`, `action_verify`, `action_expire`, `action_open_employee`, `_unlink_except_module_uninstall`

## `onehr.work.incident`

- Class: `OneHRWorkIncident`
- Registry: NEW persistent / ED3
- Source: `models/occupational_health.py`
- Fields declared here: `reference`, `employee_id`, `company_id`, `incident_at`, `work_location_id`, `location_note`, `incident_type`, `severity`, `description`, `immediate_action`, `lost_time_days`, `state`, `reported_at`, `reported_by_id`, `closed_at`, `closed_by_id`, `closure_summary`, `medical_assessment_ids`, `medical_assessment_count`
- Methods/actions: `create`, `write`, `read`, `_check_lost_time_days`, `_compute_medical_assessment_count`, `action_report`, `action_start_review`, `action_close`, `action_cancel`, `action_create_medical_assessment`, `action_open_medical_assessments`, `action_open_employee`, `_unlink_except_module_uninstall`

## `onehr.medical.assessment`

- Class: `OneHRMedicalAssessment`
- Registry: NEW persistent / ED3
- Source: `models/occupational_health.py`
- Fields declared here: `reference`, `employee_id`, `company_id`, `incident_id`, `assessment_date`, `assessment_type`, `provider_name`, `fitness_classification`, `restrictions_summary`, `next_review_date`, `confidential_notes`, `state`, `finalized_at`, `finalized_by_id`, `supersedes_id`, `superseded_by_ids`, `correction_count`
- Methods/actions: `create`, `write`, `read`, `_check_incident_employee`, `_compute_correction_count`, `action_finalize`, `action_create_correction`, `action_open_employee`, `action_open_incident`, `_unlink_except_module_uninstall`

## `onehr.disability.record`

- Class: `OneHRDisabilityRecord`
- Registry: NEW persistent / ED1
- Source: `models/occupational_health.py`
- Fields declared here: `reference`, `employee_id`, `company_id`, `category`, `accommodation_required`, `accommodation_summary`, `review_date`, `state`, `active`, `closed_at`, `closed_by_id`, `closure_note`
- Methods/actions: `create`, `write`, `read`, `action_activate`, `action_close`, `action_open_employee`, `_unlink_except_module_uninstall`

## `onehr.employee.education`

- Class: `OneHREmployeeEducation`
- Registry: NEW persistent / ED1
- Source: `models/qualification.py`
- Fields declared here: `employee_id`, `company_id`, `institution_name`, `country_id`, `qualification_level`, `qualification_name`, `field_of_study`, `study_start_date`, `study_end_date`, `completed`, `award_date`, `credential_reference`, `active`, `notes`
- Methods/actions: `_check_education_dates`, `action_mark_completed`, `action_expire_qualification`, `action_open_employee`, `_unlink_except_module_uninstall`

## `onehr.employee.employment.history`

- Class: `OneHREmployeeEmploymentHistory`
- Registry: NEW persistent / ED1
- Source: `models/qualification.py`
- Fields declared here: `employee_id`, `company_id`, `employer_name`, `job_title`, `department_name`, `work_location`, `country_id`, `reason_for_leaving`, `reference_name`, `reference_contact`, `verified`, `active`, `notes`
- Methods/actions: `_check_not_future_open_employment`, `action_verify`, `action_close_history`, `action_open_employee`, `_unlink_except_module_uninstall`

## `onehr.employee.dependent`

- Class: `OneHREmployeeDependent`
- Registry: NEW persistent / ED1
- Source: `models/relationship.py`
- Fields declared here: `employee_id`, `company_id`, `name`, `relationship`, `birth_date`, `contact_phone`, `contact_email`, `benefit_eligible`, `active`, `notes`
- Methods/actions: `_check_birth_date`, `action_expire`, `action_open_employee`, `_unlink_except_module_uninstall`

## `onehr.employee.emergency.contact`

- Class: `OneHREmployeeEmergencyContact`
- Registry: NEW persistent / ED1
- Source: `models/relationship.py`
- Fields declared here: `employee_id`, `company_id`, `name`, `relationship`, `phone`, `email`, `priority`, `is_primary`, `active`, `notes`
- Methods/actions: `_check_priority`, `_check_single_effective_primary`, `action_set_primary`, `action_expire`, `action_open_employee`, `_unlink_except_module_uninstall`

## `res.config.settings`

- Class: `ResConfigSettings`
- Registry: INHERIT_ODOO / ED0
- Source: `models/res_config_settings.py`
- Fields declared here: `onehr_identifier_mask_visible_chars`, `onehr_occ_health_enabled`, `onehr_medical_retention_days`, `onehr_profile_review_activity_days`
- Methods/actions: `_onehr_company_param_key`, `get_values`, `set_values`, `_check_onehr_settings_ranges`

## Security / UI / Report Inventory

- 4 OneHR Core HR groups, including isolated Identifier Steward and Occupational Health Officer.
- 10 ACL rows; none use `base.group_user`.
- 9 company/global record rules covering every custom persistent model.
- 5 business sequences.
- Dedicated list/form/search for all 9 custom persistent models.
- Native hr.employee form/list/search extensions.
- Odoo Settings extension.
- Safe QWeb employee profile PDF.
- 16 post-install runtime test methods.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import (
    open_records_action,
    require_corehr_officer,
    require_identifier_steward,
    require_occupational_health,
)


class HrEmployee(models.Model):
    """OneHR extension of the canonical Odoo employee identity."""

    _inherit = "hr.employee"

    onehr_employee_number = fields.Char(
        string="OneHR Employee No.",
        copy=False,
        index=True,
        tracking=True,
        help="Enterprise worker number. This is safe for internal directory display.",
    )
    onehr_profile_completeness = fields.Integer(
        string="Profile Completeness %",
        compute="_compute_onehr_profile_completeness",
        store=True,
        groups="hr.group_hr_user",
    )
    onehr_profile_status = fields.Selection(
        [
            ("incomplete", "Incomplete"),
            ("basic", "Basic"),
            ("ready", "Ready"),
        ],
        compute="_compute_onehr_profile_completeness",
        store=True,
        groups="hr.group_hr_user",
    )

    # Re-declare versioned fields on hr.employee using Odoo's own inherited
    # field pattern. The storage remains hr.version; employee is the convenient
    # canonical façade used throughout HR.
    onehr_engagement_type_id = fields.Many2one(
        related="version_id.onehr_engagement_type_id",
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )
    onehr_grade_id = fields.Many2one(
        related="version_id.onehr_grade_id",
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )
    onehr_primary_position_id = fields.Many2one(
        related="version_id.onehr_primary_position_id",
        inherited=True,
        readonly=False,
        groups="hr.group_hr_user",
    )

    onehr_dependent_ids = fields.One2many(
        "onehr.employee.dependent", "employee_id", string="Dependents",
        groups="onehr_corehr.group_onehr_corehr_officer",
    )
    onehr_emergency_contact_ids = fields.One2many(
        "onehr.employee.emergency.contact", "employee_id", string="Emergency Contacts",
        groups="onehr_corehr.group_onehr_corehr_officer",
    )
    onehr_identifier_ids = fields.One2many(
        "onehr.employee.identifier", "employee_id", string="Identifiers",
        groups="onehr_corehr.group_onehr_identifier_steward",
    )
    onehr_education_ids = fields.One2many(
        "onehr.employee.education", "employee_id", string="Education",
        groups="onehr_corehr.group_onehr_corehr_officer",
    )
    onehr_employment_history_ids = fields.One2many(
        "onehr.employee.employment.history", "employee_id", string="External Employment History",
        groups="onehr_corehr.group_onehr_corehr_officer",
    )

    onehr_dependent_count = fields.Integer(compute="_compute_onehr_counts", groups="onehr_corehr.group_onehr_corehr_officer")
    onehr_emergency_contact_count = fields.Integer(compute="_compute_onehr_counts", groups="onehr_corehr.group_onehr_corehr_officer")
    onehr_identifier_count = fields.Integer(
        compute="_compute_onehr_identifier_count",
        compute_sudo=True,
        groups="onehr_corehr.group_onehr_identifier_steward",
    )
    onehr_education_count = fields.Integer(compute="_compute_onehr_counts", groups="onehr_corehr.group_onehr_corehr_officer")
    onehr_employment_history_count = fields.Integer(compute="_compute_onehr_counts", groups="onehr_corehr.group_onehr_corehr_officer")
    onehr_checklist_count = fields.Integer(compute="_compute_onehr_counts", groups="hr.group_hr_user")

    onehr_work_incident_count = fields.Integer(compute="_compute_onehr_restricted_counts", groups="onehr_corehr.group_onehr_occupational_health_officer")
    onehr_medical_assessment_count = fields.Integer(compute="_compute_onehr_restricted_counts", groups="onehr_corehr.group_onehr_occupational_health_officer")
    onehr_disability_record_count = fields.Integer(compute="_compute_onehr_restricted_counts", groups="onehr_corehr.group_onehr_occupational_health_officer")

    onehr_accommodation_required = fields.Boolean(
        string="Accommodation Required",
        compute="_compute_onehr_accommodation_required",
        compute_sudo=True,
        groups="hr.group_hr_manager,onehr_corehr.group_onehr_occupational_health_officer",
        help="Minimum-necessary derived flag. Detailed disability records remain restricted.",
    )

    _onehr_employee_number_unique = models.Constraint(
        "unique(company_id, onehr_employee_number)",
        "OneHR Employee Number must be unique within a company.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if not vals.get("onehr_employee_number"):
                vals["onehr_employee_number"] = self.env["ir.sequence"].next_by_code(
                    "onehr.employee"
                )
            prepared.append(vals)
        return super().create(prepared)

    @api.depends(
        "onehr_employee_number",
        "name",
        "work_email",
        "work_phone",
        "private_email",
        "private_phone",
        "birthday",
        "country_id",
        "department_id",
        "job_id",
    )
    def _compute_onehr_profile_completeness(self):
        for employee in self:
            checks = (
                employee.onehr_employee_number,
                employee.name,
                employee.work_email,
                employee.work_phone,
                employee.private_email,
                employee.private_phone,
                employee.birthday,
                employee.country_id,
                employee.department_id,
                employee.job_id,
            )
            score = round(sum(bool(value) for value in checks) * 100 / len(checks))
            employee.onehr_profile_completeness = score
            employee.onehr_profile_status = (
                "ready" if score >= 80 else "basic" if score >= 50 else "incomplete"
            )

    def _compute_onehr_counts(self):
        models_by_field = {
            "onehr_dependent_count": "onehr.employee.dependent",
            "onehr_emergency_contact_count": "onehr.employee.emergency.contact",
            "onehr_education_count": "onehr.employee.education",
            "onehr_employment_history_count": "onehr.employee.employment.history",
            "onehr_checklist_count": "onehr.checklist.instance",
        }
        for employee in self:
            for field_name, model_name in models_by_field.items():
                employee[field_name] = self.env[model_name].search_count(
                    [("employee_id", "=", employee.id)]
                )

    def _compute_onehr_identifier_count(self):
        for employee in self:
            employee.onehr_identifier_count = self.env["onehr.employee.identifier"].search_count(
                [("employee_id", "=", employee.id)]
            )

    def _compute_onehr_restricted_counts(self):
        for employee in self:
            employee.onehr_work_incident_count = self.env["onehr.work.incident"].search_count(
                [("employee_id", "=", employee.id)]
            )
            employee.onehr_medical_assessment_count = self.env["onehr.medical.assessment"].search_count(
                [("employee_id", "=", employee.id)]
            )
            employee.onehr_disability_record_count = self.env["onehr.disability.record"].search_count(
                [("employee_id", "=", employee.id)]
            )

    def _compute_onehr_accommodation_required(self):
        today = fields.Date.context_today(self)
        Record = self.env["onehr.disability.record"]
        for employee in self:
            employee.onehr_accommodation_required = bool(
                Record.search_count(
                    [
                        ("employee_id", "=", employee.id),
                        ("state", "=", "active"),
                        ("accommodation_required", "=", True),
                        ("valid_from", "<=", today),
                        "|",
                        ("valid_to", "=", False),
                        ("valid_to", ">=", today),
                    ],
                    limit=1,
                )
            )

    def _open_employee_children(self, model_name, title, default_context=None):
        self.ensure_one()
        return open_records_action(
            name=_(title, self.display_name),
            res_model=model_name,
            domain=[("employee_id", "=", self.id)],
            context={"default_employee_id": self.id, **(default_context or {})},
        )

    def action_open_onehr_dependents(self):
        require_corehr_officer(self.env)
        return self._open_employee_children("onehr.employee.dependent", "Dependents — %s")

    def action_open_onehr_emergency_contacts(self):
        require_corehr_officer(self.env)
        return self._open_employee_children("onehr.employee.emergency.contact", "Emergency Contacts — %s")

    def action_open_onehr_identifiers(self):
        require_identifier_steward(self.env)
        return self._open_employee_children("onehr.employee.identifier", "Identifiers — %s")

    def action_open_onehr_education(self):
        require_corehr_officer(self.env)
        return self._open_employee_children("onehr.employee.education", "Education — %s")

    def action_open_onehr_employment_history(self):
        require_corehr_officer(self.env)
        return self._open_employee_children("onehr.employee.employment.history", "External Employment — %s")

    def action_open_onehr_checklists(self):
        self.ensure_one()
        return open_records_action(
            name=_("Lifecycle Checklists — %s", self.display_name),
            res_model="onehr.checklist.instance",
            domain=[("employee_id", "=", self.id)],
            context={"default_employee_id": self.id, "default_company_id": self.company_id.id},
        )

    def action_open_onehr_work_incidents(self):
        require_occupational_health(self.env)
        return self._open_employee_children("onehr.work.incident", "Work Incidents — %s")

    def action_open_onehr_medical_assessments(self):
        require_occupational_health(self.env)
        return self._open_employee_children("onehr.medical.assessment", "Medical Assessments — %s")

    def action_open_onehr_disability_records(self):
        require_occupational_health(self.env)
        return self._open_employee_children("onehr.disability.record", "Accommodation Records — %s")


class HrEmployeePublic(models.Model):
    """Expose only explicitly approved OneHR directory-safe fields."""

    _inherit = "hr.employee.public"

    onehr_employee_number = fields.Char(readonly=True)

    # Deliberately absent:
    # dependents, identifiers, medical/disability, profile completeness,
    # private contact data, grade and any restricted OneHR payload.


class HrVersion(models.Model):
    """OneHR versioned employment facts stored on Odoo's canonical hr.version."""

    _inherit = "hr.version"

    onehr_engagement_type_id = fields.Many2one(
        "onehr.engagement.type",
        string="OneHR Engagement Type",
        ondelete="restrict",
        tracking=True,
        groups="hr.group_hr_user",
    )
    onehr_grade_id = fields.Many2one(
        "onehr.grade",
        string="OneHR Grade",
        ondelete="restrict",
        tracking=True,
        groups="hr.group_hr_user",
    )
    onehr_primary_position_id = fields.Many2one(
        "onehr.position",
        string="Primary OneHR Position",
        ondelete="restrict",
        tracking=True,
        groups="hr.group_hr_user",
        help=(
            "Versioned target field for the approved primary OneHR assignment. "
            "onehr_assignment remains the owner of assignment transactions."
        ),
    )

    @api.constrains(
        "company_id",
        "date_version",
        "employee_type",
        "onehr_engagement_type_id",
        "onehr_grade_id",
        "onehr_primary_position_id",
    )
    def _check_onehr_versioned_reference_integrity(self):
        for version in self:
            as_of = version.date_version or fields.Date.context_today(version)

            engagement = version.onehr_engagement_type_id
            if engagement:
                if engagement.company_id and engagement.company_id != version.company_id:
                    raise ValidationError(_("Engagement Type must belong to the version company or be global."))
                if not engagement.active or not engagement.is_effective_on(as_of):
                    raise ValidationError(_("Engagement Type must be effective on the version date."))
                if engagement.native_employee_type != version.employee_type:
                    raise ValidationError(
                        _("OneHR Engagement Type must map to the selected native Employee Type.")
                    )

            grade = version.onehr_grade_id
            if grade:
                if grade.company_id and grade.company_id != version.company_id:
                    raise ValidationError(_("Grade must belong to the version company or be global."))
                if not grade.active or not grade.is_effective_on(as_of):
                    raise ValidationError(_("Grade must be effective on the version date."))

            position = version.onehr_primary_position_id
            if position:
                if position.company_id != version.company_id:
                    raise ValidationError(_("Primary Position must belong to the version company."))
                if not position.active or not position.is_effective_on(as_of):
                    raise ValidationError(_("Primary Position must be effective on the version date."))

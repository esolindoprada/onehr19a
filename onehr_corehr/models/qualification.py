from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_record_action, require_corehr_officer


class OneHREmployeeEducation(models.Model):
    _name = "onehr.employee.education"
    _description = "OneHR Employee Education"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "employee_id, award_date desc, id desc"
    _rec_name = "institution_name"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, index=True)
    institution_name = fields.Char(required=True, tracking=True)
    country_id = fields.Many2one("res.country", ondelete="restrict")
    qualification_level = fields.Selection(
        [
            ("secondary", "Secondary"),
            ("diploma", "Diploma"),
            ("bachelor", "Bachelor"),
            ("master", "Master"),
            ("doctorate", "Doctorate"),
            ("professional", "Professional"),
            ("certificate", "Certificate"),
            ("other", "Other"),
        ],
        required=True,
        tracking=True,
    )
    qualification_name = fields.Char(required=True, tracking=True)
    field_of_study = fields.Char(tracking=True)
    study_start_date = fields.Date()
    study_end_date = fields.Date()
    completed = fields.Boolean(tracking=True)
    award_date = fields.Date(tracking=True)
    credential_reference = fields.Char(
        help="Reference only. Supporting documents belong to onehr_document."
    )
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text()

    @api.constrains("study_start_date", "study_end_date", "award_date")
    def _check_education_dates(self):
        for record in self:
            if (
                record.study_start_date
                and record.study_end_date
                and record.study_end_date < record.study_start_date
            ):
                raise ValidationError(_("Study End Date cannot be before Study Start Date."))
            if record.award_date and record.study_start_date and record.award_date < record.study_start_date:
                raise ValidationError(_("Award Date cannot be before Study Start Date."))

    def action_mark_completed(self):
        require_corehr_officer(self.env)
        for record in self:
            record.write(
                {
                    "completed": True,
                    "award_date": record.award_date or fields.Date.context_today(record),
                }
            )
        return True

    def action_expire_qualification(self):
        require_corehr_officer(self.env)
        self.write({"valid_to": fields.Date.context_today(self), "active": False})
        return True

    def action_open_employee(self):
        self.ensure_one()
        require_corehr_officer(self.env)
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise ValidationError(_("Education history cannot be deleted. Archive/end-date it instead."))


class OneHREmployeeEmploymentHistory(models.Model):
    """Prior external employment only; OneHR internal placement belongs to assignment."""

    _name = "onehr.employee.employment.history"
    _description = "OneHR Prior External Employment"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "employee_id, valid_from desc, id desc"
    _rec_name = "employer_name"

    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, index=True)
    employer_name = fields.Char(required=True, tracking=True)
    job_title = fields.Char(required=True, tracking=True)
    department_name = fields.Char()
    work_location = fields.Char()
    country_id = fields.Many2one("res.country", ondelete="restrict")
    reason_for_leaving = fields.Char()
    reference_name = fields.Char()
    reference_contact = fields.Char()
    verified = fields.Boolean(tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    notes = fields.Text()

    @api.constrains("valid_from", "valid_to")
    def _check_not_future_open_employment(self):
        today = fields.Date.context_today(self)
        for record in self:
            if record.valid_from > today:
                raise ValidationError(_("Prior external employment cannot start in the future."))

    def action_verify(self):
        require_corehr_officer(self.env)
        self.write({"verified": True})
        return True

    def action_close_history(self):
        require_corehr_officer(self.env)
        self.write({"valid_to": fields.Date.context_today(self), "active": False})
        return True

    def action_open_employee(self):
        self.ensure_one()
        require_corehr_officer(self.env)
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise ValidationError(_("Prior-employment history cannot be deleted. Archive/end-date it instead."))

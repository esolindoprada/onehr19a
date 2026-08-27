from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import (
    open_record_action,
    open_records_action,
    require_occupational_health,
)
from .sensitive_access import log_sensitive_change, log_sensitive_read


class OneHRWorkIncident(models.Model):
    _name = "onehr.work.incident"
    _description = "OneHR Restricted Work Incident"
    _inherit = ["onehr.mixin.audit"]
    _order = "incident_at desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _("New"))
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, index=True)
    incident_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True, tracking=True)
    work_location_id = fields.Many2one("hr.work.location", ondelete="restrict", tracking=True)
    location_note = fields.Char()
    incident_type = fields.Selection(
        [
            ("injury", "Injury"),
            ("illness", "Work-Related Illness"),
            ("near_miss", "Near Miss"),
            ("exposure", "Exposure"),
            ("ergonomic", "Ergonomic"),
            ("other", "Other"),
        ],
        required=True,
        index=True,
        tracking=True,
    )
    severity = fields.Selection(
        [
            ("minor", "Minor"),
            ("moderate", "Moderate"),
            ("serious", "Serious"),
            ("critical", "Critical"),
        ],
        required=True,
        default="minor",
        index=True,
        tracking=True,
    )
    description = fields.Text(required=True, groups="onehr_corehr.group_onehr_occupational_health_officer")
    immediate_action = fields.Text(groups="onehr_corehr.group_onehr_occupational_health_officer")
    lost_time_days = fields.Float(default=0.0)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("reported", "Reported"),
            ("under_review", "Under Review"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    reported_at = fields.Datetime(readonly=True)
    reported_by_id = fields.Many2one("res.users", readonly=True)
    closed_at = fields.Datetime(readonly=True)
    closed_by_id = fields.Many2one("res.users", readonly=True)
    closure_summary = fields.Text(groups="onehr_corehr.group_onehr_occupational_health_officer")
    medical_assessment_ids = fields.One2many("onehr.medical.assessment", "incident_id", string="Medical Assessments")
    medical_assessment_count = fields.Integer(compute="_compute_medical_assessment_count")

    @api.model_create_multi
    def create(self, vals_list):
        require_occupational_health(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "draft") != "draft":
                raise AccessError(_("New work incidents must start in Draft."))
            vals["state"] = "draft"
            if vals.get("reference") in (False, _("New"), "New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code("onehr.work.incident") or _("New")
            prepared.append(vals)
        records = super().create(prepared)
        for record in records:
            log_sensitive_change(
                record,
                action="create",
                summary=_("Restricted work incident created"),
                severity="high",
                metadata={"severity": record.severity, "incident_type": record.incident_type},
            )
        return records

    def write(self, vals):
        if "state" in vals and not self.env.context.get("onehr_incident_state_action"):
            if any(vals["state"] != record.state for record in self):
                raise AccessError(_("Use controlled Work Incident workflow actions to change state."))

        protected = {
            "employee_id", "company_id", "incident_at", "work_location_id",
            "location_note", "incident_type", "severity", "description",
            "immediate_action", "lost_time_days",
        }
        if protected & set(vals) and any(record.state in ("closed", "cancelled") for record in self):
            raise AccessError(_("Closed/cancelled work-incident evidence is immutable."))

        result = super().write(vals)
        if set(vals) & (protected | {"state"}):
            for record in self:
                log_sensitive_change(
                    record,
                    action="update",
                    summary=_("Restricted work incident updated"),
                    severity="high",
                    metadata={"changed_fields": sorted(set(vals)), "state": record.state},
                )
        return result

    def read(self, fields=None, load="_classic_read"):
        result = super().read(fields=fields, load=load)
        log_sensitive_read(
            self,
            fields,
            {"description", "immediate_action", "closure_summary"},
            _("Work Incident"),
        )
        return result

    @api.constrains("lost_time_days")
    def _check_lost_time_days(self):
        for record in self:
            if record.lost_time_days < 0:
                raise ValidationError(_("Lost Time Days cannot be negative."))

    def _compute_medical_assessment_count(self):
        for record in self:
            record.medical_assessment_count = len(record.medical_assessment_ids)

    def action_report(self):
        require_occupational_health(self.env)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft incidents can be reported."))
            record.with_context(onehr_incident_state_action=True).write(
                {
                    "state": "reported",
                    "reported_at": fields.Datetime.now(),
                    "reported_by_id": self.env.user.id,
                }
            )
        return True

    def action_start_review(self):
        require_occupational_health(self.env)
        for record in self:
            if record.state != "reported":
                raise UserError(_("Only Reported incidents can enter review."))
            record.with_context(onehr_incident_state_action=True).write({"state": "under_review"})
        return True

    def action_close(self):
        require_occupational_health(self.env)
        for record in self:
            if record.state not in ("reported", "under_review"):
                raise UserError(_("Only Reported or Under Review incidents can be closed."))
            if not record.closure_summary:
                raise ValidationError(_("Closure Summary is required before closing a Work Incident."))
            record.with_context(onehr_incident_state_action=True).write(
                {
                    "state": "closed",
                    "closed_at": fields.Datetime.now(),
                    "closed_by_id": self.env.user.id,
                }
            )
        return True

    def action_cancel(self):
        require_occupational_health(self.env)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only a Draft incident may be cancelled."))
            record.with_context(onehr_incident_state_action=True).write({"state": "cancelled"})
        return True

    def action_create_medical_assessment(self):
        self.ensure_one()
        require_occupational_health(self.env)
        assessment = self.env["onehr.medical.assessment"].create(
            {
                "employee_id": self.employee_id.id,
                "incident_id": self.id,
                "assessment_date": fields.Date.context_today(self),
                "assessment_type": "incident_followup",
            }
        )
        return open_record_action(
            name=assessment.display_name,
            res_model="onehr.medical.assessment",
            res_id=assessment.id,
        )

    def action_open_medical_assessments(self):
        self.ensure_one()
        require_occupational_health(self.env)
        return open_records_action(
            name=_("Medical Assessments — %s", self.reference),
            res_model="onehr.medical.assessment",
            domain=[("incident_id", "=", self.id)],
            context={"default_employee_id": self.employee_id.id, "default_incident_id": self.id},
        )

    def action_open_employee(self):
        self.ensure_one()
        require_occupational_health(self.env)
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise AccessError(_("Work-incident evidence cannot be deleted."))


class OneHRMedicalAssessment(models.Model):
    _name = "onehr.medical.assessment"
    _description = "OneHR Restricted Medical Assessment"
    _inherit = ["onehr.mixin.audit"]
    _order = "assessment_date desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _("New"))
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, index=True)
    incident_id = fields.Many2one("onehr.work.incident", ondelete="restrict", index=True, tracking=True)
    assessment_date = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    assessment_type = fields.Selection(
        [
            ("pre_employment", "Pre-Employment"),
            ("periodic", "Periodic"),
            ("return_to_work", "Return to Work"),
            ("incident_followup", "Incident Follow-up"),
            ("fitness", "Fitness for Work"),
            ("other", "Other"),
        ],
        required=True,
        default="periodic",
        tracking=True,
    )
    provider_name = fields.Char(groups="onehr_corehr.group_onehr_occupational_health_officer")
    fitness_classification = fields.Selection(
        [
            ("fit", "Fit"),
            ("fit_with_restrictions", "Fit with Restrictions"),
            ("temporarily_unfit", "Temporarily Unfit"),
            ("unfit", "Unfit"),
            ("confidential", "Confidential / Not Disclosed"),
        ],
        required=True,
        default="confidential",
        tracking=True,
        groups="onehr_corehr.group_onehr_occupational_health_officer",
    )
    restrictions_summary = fields.Text(
        groups="onehr_corehr.group_onehr_occupational_health_officer",
        help="Store only minimum-necessary work restrictions; avoid diagnosis details.",
    )
    next_review_date = fields.Date()
    confidential_notes = fields.Text(groups="onehr_corehr.group_onehr_occupational_health_officer")
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("finalized", "Finalized"),
            ("superseded", "Superseded"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    finalized_at = fields.Datetime(readonly=True)
    finalized_by_id = fields.Many2one("res.users", readonly=True)
    supersedes_id = fields.Many2one("onehr.medical.assessment", readonly=True, ondelete="restrict")
    superseded_by_ids = fields.One2many("onehr.medical.assessment", "supersedes_id", string="Corrections")
    correction_count = fields.Integer(compute="_compute_correction_count")

    @api.model_create_multi
    def create(self, vals_list):
        require_occupational_health(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "draft") != "draft":
                raise AccessError(_("New medical assessments must start in Draft."))
            vals["state"] = "draft"
            if vals.get("reference") in (False, _("New"), "New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code("onehr.medical.assessment") or _("New")
            prepared.append(vals)
        records = super().create(prepared)
        for record in records:
            log_sensitive_change(
                record,
                action="create",
                summary=_("Restricted medical assessment created"),
                severity="critical",
                metadata={"assessment_type": record.assessment_type},
            )
        return records

    def write(self, vals):
        if "state" in vals and not self.env.context.get("onehr_medical_state_action"):
            if any(vals["state"] != record.state for record in self):
                raise AccessError(_("Use controlled Medical Assessment workflow actions to change state."))

        protected = {
            "employee_id", "incident_id", "assessment_date", "assessment_type",
            "provider_name", "fitness_classification", "restrictions_summary",
            "next_review_date", "confidential_notes",
        }
        if protected & set(vals) and any(record.state in ("finalized", "superseded") for record in self):
            raise AccessError(
                _("Finalized medical evidence is immutable. Create a superseding correction instead.")
            )

        result = super().write(vals)
        if set(vals) & (protected | {"state"}):
            for record in self:
                log_sensitive_change(
                    record,
                    action="update",
                    summary=_("Restricted medical assessment updated"),
                    severity="critical",
                    metadata={"changed_fields": sorted(set(vals)), "state": record.state},
                )
        return result

    def read(self, fields=None, load="_classic_read"):
        result = super().read(fields=fields, load=load)
        log_sensitive_read(
            self,
            fields,
            {"provider_name", "fitness_classification", "restrictions_summary", "confidential_notes"},
            _("Medical Assessment"),
        )
        return result

    @api.constrains("incident_id", "employee_id")
    def _check_incident_employee(self):
        for record in self:
            if record.incident_id and record.incident_id.employee_id != record.employee_id:
                raise ValidationError(_("Medical Assessment employee must match the linked Work Incident employee."))

    def _compute_correction_count(self):
        for record in self:
            record.correction_count = len(record.superseded_by_ids)

    def action_finalize(self):
        require_occupational_health(self.env)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft medical assessments can be finalized."))
            record.with_context(onehr_medical_state_action=True).write(
                {
                    "state": "finalized",
                    "finalized_at": fields.Datetime.now(),
                    "finalized_by_id": self.env.user.id,
                }
            )
        return True

    def action_create_correction(self):
        self.ensure_one()
        require_occupational_health(self.env)
        if self.state != "finalized":
            raise UserError(_("Only a Finalized assessment can be corrected by supersession."))

        correction = self.create(
            {
                "employee_id": self.employee_id.id,
                "incident_id": self.incident_id.id if self.incident_id else False,
                "assessment_date": fields.Date.context_today(self),
                "assessment_type": self.assessment_type,
                "provider_name": self.provider_name,
                "fitness_classification": self.fitness_classification,
                "restrictions_summary": self.restrictions_summary,
                "next_review_date": self.next_review_date,
                "confidential_notes": False,
                "supersedes_id": self.id,
            }
        )
        self.with_context(onehr_medical_state_action=True).write({"state": "superseded"})
        return open_record_action(
            name=correction.display_name,
            res_model="onehr.medical.assessment",
            res_id=correction.id,
        )

    def action_open_employee(self):
        self.ensure_one()
        require_occupational_health(self.env)
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    def action_open_incident(self):
        self.ensure_one()
        require_occupational_health(self.env)
        if not self.incident_id:
            raise UserError(_("This assessment is not linked to a Work Incident."))
        return open_record_action(name=self.incident_id.display_name, res_model="onehr.work.incident", res_id=self.incident_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise AccessError(_("Medical-assessment evidence cannot be deleted."))


class OneHRDisabilityRecord(models.Model):
    """Minimum-necessary restricted disability/accommodation administration."""

    _name = "onehr.disability.record"
    _description = "OneHR Restricted Disability / Accommodation Record"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "valid_from desc, id desc"
    _rec_name = "reference"

    reference = fields.Char(required=True, copy=False, readonly=True, index=True, default=lambda self: _("New"))
    employee_id = fields.Many2one("hr.employee", required=True, ondelete="restrict", index=True, tracking=True)
    company_id = fields.Many2one(related="employee_id.company_id", store=True, index=True)
    category = fields.Selection(
        [
            ("mobility", "Mobility"),
            ("sensory", "Sensory"),
            ("cognitive", "Cognitive / Neurodiversity"),
            ("chronic", "Chronic / Long-term"),
            ("temporary", "Temporary"),
            ("other", "Other / Confidential"),
        ],
        required=True,
        default="other",
        tracking=True,
    )
    accommodation_required = fields.Boolean(tracking=True)
    accommodation_summary = fields.Text(
        groups="onehr_corehr.group_onehr_occupational_health_officer",
        help="Minimum-necessary accommodation requirement; do not store diagnosis unless legally required.",
    )
    review_date = fields.Date()
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("closed", "Closed"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    active = fields.Boolean(default=True, tracking=True)
    closed_at = fields.Datetime(readonly=True)
    closed_by_id = fields.Many2one("res.users", readonly=True)
    closure_note = fields.Text(groups="onehr_corehr.group_onehr_occupational_health_officer")

    @api.model_create_multi
    def create(self, vals_list):
        require_occupational_health(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("state", "draft") != "draft":
                raise AccessError(_("New accommodation records must start in Draft."))
            vals["state"] = "draft"
            if vals.get("reference") in (False, _("New"), "New"):
                vals["reference"] = self.env["ir.sequence"].next_by_code("onehr.disability.record") or _("New")
            prepared.append(vals)
        records = super().create(prepared)
        for record in records:
            log_sensitive_change(
                record,
                action="create",
                summary=_("Restricted accommodation record created"),
                severity="critical",
                metadata={"raw_diagnosis_stored": False},
            )
        return records

    def write(self, vals):
        if "state" in vals and not self.env.context.get("onehr_disability_state_action"):
            if any(vals["state"] != record.state for record in self):
                raise AccessError(_("Use controlled Accommodation workflow actions to change state."))

        protected = {
            "employee_id", "category", "accommodation_required",
            "accommodation_summary", "valid_from", "valid_to", "review_date",
        }
        if protected & set(vals) and any(record.state == "closed" for record in self):
            raise AccessError(_("Closed accommodation evidence is immutable."))

        result = super().write(vals)
        if set(vals) & (protected | {"state"}):
            for record in self:
                log_sensitive_change(
                    record,
                    action="update",
                    summary=_("Restricted accommodation record updated"),
                    severity="critical",
                    metadata={"changed_fields": sorted(set(vals)), "state": record.state},
                )
        return result

    def read(self, fields=None, load="_classic_read"):
        result = super().read(fields=fields, load=load)
        log_sensitive_read(
            self,
            fields,
            {"category", "accommodation_required", "accommodation_summary", "closure_note"},
            _("Accommodation Record"),
        )
        return result

    def action_activate(self):
        require_occupational_health(self.env)
        for record in self:
            if record.state != "draft":
                raise UserError(_("Only Draft accommodation records can be activated."))
            record.with_context(onehr_disability_state_action=True).write({"state": "active"})
        return True

    def action_close(self):
        require_occupational_health(self.env)
        for record in self:
            if record.state != "active":
                raise UserError(_("Only Active accommodation records can be closed."))
            record.with_context(onehr_disability_state_action=True).write(
                {
                    "state": "closed",
                    "active": False,
                    "valid_to": record.valid_to or fields.Date.context_today(record),
                    "closed_at": fields.Datetime.now(),
                    "closed_by_id": self.env.user.id,
                }
            )
        return True

    def action_open_employee(self):
        self.ensure_one()
        require_occupational_health(self.env)
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise AccessError(_("Disability/accommodation evidence cannot be deleted."))

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_hiring_manager, require_recruiter, require_recruitment_manager


class OneHRInterviewTemplate(models.Model):
    """Versioned structured interview and scorecard definition (ED2)."""

    _name = "onehr.interview.template"
    _description = "OneHR Interview Template"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.effective.dated"]
    _order = "code, version desc, id desc"

    code = fields.Char(required=True, index=True, tracking=True)
    name = fields.Char(required=True, index=True, tracking=True)
    version = fields.Integer(required=True, default=1, readonly=True, tracking=True)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True,
        tracking=True, ondelete="cascade",
        help="Leave empty only for a deliberately global template.",
    )
    job_id = fields.Many2one(
        "hr.job", string="Applicable Job", index=True, tracking=True,
        ondelete="set null", check_company=True,
        help="Optional job-specific template. Empty means reusable across jobs.",
    )
    interview_type = fields.Selection(
        [
            ("screening", "Screening"),
            ("technical", "Technical"),
            ("behavioral", "Behavioral"),
            ("panel", "Panel"),
            ("executive", "Executive / Final"),
        ],
        required=True, default="behavioral", index=True, tracking=True,
    )
    duration_minutes = fields.Integer(required=True, default=60, tracking=True)
    minimum_overall_score = fields.Float(default=3.0, tracking=True)
    interviewer_guidance = fields.Html(sanitize=True)
    scorecard_definition = fields.PropertiesDefinition(
        string="Scorecard Criteria",
        help="Human-friendly structured criteria used by score records without executable expressions.",
    )
    state = fields.Selection(
        [("draft", "Draft"), ("active", "Active"), ("retired", "Retired")],
        required=True, default="draft", index=True, tracking=True, copy=False,
    )
    session_ids = fields.One2many("onehr.interview.session", "template_id", string="Interview Sessions")
    session_count = fields.Integer(compute="_compute_session_count")

    @api.model_create_multi
    def create(self, vals_list):
        require_recruitment_manager(self)
        for values in vals_list:
            if values.get("code"):
                values["code"] = values["code"].strip().upper()
        return super().create(vals_list)

    def write(self, values):
        require_recruitment_manager(self)
        protected = {"code", "company_id", "job_id", "scorecard_definition", "minimum_overall_score", "valid_from", "valid_to"}
        if protected.intersection(values) and self.filtered(lambda rec: rec.state != "draft"):
            raise AccessError(_("Published interview template versions are historical definitions and cannot be rewritten."))
        if "code" in values and values["code"]:
            values["code"] = values["code"].strip().upper()
        return super().write(values)

    @api.depends("session_ids")
    def _compute_session_count(self):
        for template in self:
            template.session_count = len(template.session_ids)

    @api.constrains("duration_minutes", "minimum_overall_score")
    def _check_numeric_values(self):
        for template in self:
            if template.duration_minutes <= 0:
                raise ValidationError(_("Interview duration must be greater than zero."))
            if not 0.0 <= template.minimum_overall_score <= 5.0:
                raise ValidationError(_("Minimum overall score must be between 0 and 5."))

    @api.constrains("code", "version", "company_id", "job_id")
    def _check_unique_version(self):
        for template in self:
            domain = [
                ("id", "!=", template.id),
                ("code", "=", template.code),
                ("version", "=", template.version),
                ("company_id", "=", template.company_id.id or False),
                ("job_id", "=", template.job_id.id or False),
            ]
            if self.search_count(domain):
                raise ValidationError(_("Interview template code/version must be unique in its company and job scope."))

    @api.constrains("state", "valid_from", "valid_to", "code", "company_id", "job_id")
    def _check_active_overlap(self):
        for template in self.filtered(lambda rec: rec.state == "active"):
            domain = template._overlap_domain(
                ["code", "company_id", "job_id"],
                extra_domain=[("state", "=", "active")],
            )
            if self.search_count(domain):
                raise ValidationError(_("Active interview template versions may not overlap for the same scope."))

    def action_activate(self):
        self.ensure_one()
        require_recruitment_manager(self)
        if self.state != "draft":
            raise UserError(_("Only a draft interview template can be activated."))
        self.write({"state": "active"})
        return True

    def action_retire(self):
        self.ensure_one()
        require_recruitment_manager(self)
        if self.state != "active":
            raise UserError(_("Only an active interview template can be retired."))
        # The state change itself is controlled; definition fields stay frozen.
        super(OneHRInterviewTemplate, self).write({"state": "retired"})
        return True

    def action_create_new_version(self):
        self.ensure_one()
        require_recruitment_manager(self)
        values = {
            "code": self.code,
            "name": self.name,
            "version": self.version + 1,
            "company_id": self.company_id.id,
            "job_id": self.job_id.id,
            "interview_type": self.interview_type,
            "duration_minutes": self.duration_minutes,
            "minimum_overall_score": self.minimum_overall_score,
            "interviewer_guidance": self.interviewer_guidance,
            "scorecard_definition": self.scorecard_definition,
            "valid_from": fields.Date.today(),
            "valid_to": False,
            "state": "draft",
        }
        new_version = self.create(values)
        return open_record_action(name=_("New Interview Template Version"), res_model=self._name, res_id=new_version.id)

    def action_open_sessions(self):
        self.ensure_one()
        return open_records_action(
            name=_("Interview Sessions — %s", self.display_name), res_model="onehr.interview.session",
            domain=[("template_id", "=", self.id)], context={"default_template_id": self.id},
            view_mode="calendar,list,form",
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        if any(rec.state != "draft" or rec.session_ids for rec in self):
            raise UserError(_("Only unused draft interview templates may be deleted."))


class OneHRInterviewSession(models.Model):
    """Scheduled interview event and final evidence (ED3)."""

    _name = "onehr.interview.session"
    _description = "OneHR Interview Session"
    _inherit = ["onehr.mixin.audit"]
    _order = "scheduled_start desc, id desc"

    name = fields.Char(required=True, default=lambda self: _("Interview"), tracking=True, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True, tracking=True, ondelete="restrict"
    )
    applicant_id = fields.Many2one(
        "hr.applicant", required=True, index=True, tracking=True, ondelete="restrict", check_company=True
    )
    requisition_id = fields.Many2one(
        "onehr.recruitment.requisition", index=True, tracking=True, ondelete="set null", check_company=True
    )
    template_id = fields.Many2one(
        "onehr.interview.template", required=True, index=True, tracking=True, ondelete="restrict", check_company=True
    )
    template_code_snapshot = fields.Char(readonly=True, copy=False)
    template_name_snapshot = fields.Char(readonly=True, copy=False)
    template_version_snapshot = fields.Integer(readonly=True, copy=False)
    scorecard_definition_snapshot = fields.Json(readonly=True, copy=False)
    scheduled_start = fields.Datetime(required=True, default=fields.Datetime.now, index=True, tracking=True)
    scheduled_end = fields.Datetime(
        required=True,
        default=lambda self: fields.Datetime.now() + timedelta(hours=1),
        index=True, tracking=True,
    )
    interviewer_user_ids = fields.Many2many(
        "res.users", "onehr_interview_session_user_rel", "session_id", "user_id",
        string="Interviewers", tracking=True,
    )
    lead_interviewer_user_id = fields.Many2one(
        "res.users", string="Lead Interviewer", index=True, tracking=True, ondelete="set null"
    )
    location = fields.Char(tracking=True)
    meeting_url = fields.Char(tracking=True)
    calendar_event_id = fields.Many2one("calendar.event", readonly=True, copy=False, ondelete="set null")
    state = fields.Selection(
        [
            ("planned", "Planned"),
            ("confirmed", "Confirmed"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("no_show", "No Show"),
        ],
        required=True, default="planned", index=True, tracking=True, copy=False,
    )
    outcome = fields.Selection(
        [("proceed", "Proceed"), ("hold", "Hold"), ("reject", "Reject")],
        tracking=True, copy=False,
    )
    score_ids = fields.One2many("onehr.interview.score", "session_id", string="Scorecards")
    score_count = fields.Integer(compute="_compute_score_summary")
    finalized_score_count = fields.Integer(compute="_compute_score_summary")
    average_overall_score = fields.Float(compute="_compute_score_summary", digits=(16, 2))
    completed_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    cancellation_reason = fields.Text(copy=False, tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        require_recruiter(self)
        templates = self.env["onehr.interview.template"]
        for values in vals_list:
            template = templates.browse(values.get("template_id"))
            applicant = self.env["hr.applicant"].browse(values.get("applicant_id"))
            if not template or template.state != "active":
                raise ValidationError(_("Interview sessions require an active interview template."))
            scheduled = fields.Datetime.to_datetime(values.get("scheduled_start") or fields.Datetime.now())
            if not template.is_effective_on(scheduled.date()):
                raise ValidationError(_("The selected interview template is not effective on the interview date."))
            values.setdefault("company_id", applicant.company_id.id or self.env.company.id)
            values.setdefault("requisition_id", applicant.onehr_requisition_id.id)
            values.setdefault("name", _("%s — %s", template.name, applicant.partner_name or applicant.display_name))
            values.update({
                "template_code_snapshot": template.code,
                "template_name_snapshot": template.name,
                "template_version_snapshot": template.version,
                "scorecard_definition_snapshot": template.scorecard_definition or {},
            })
        return super().create(vals_list)

    def write(self, values):
        historical = {"applicant_id", "requisition_id", "template_id", "company_id", "template_code_snapshot", "template_name_snapshot", "template_version_snapshot", "scorecard_definition_snapshot"}
        if historical.intersection(values) and self.filtered(lambda rec: rec.state != "planned"):
            raise AccessError(_("Confirmed/completed interview evidence cannot be reassigned or rewritten."))
        if self.filtered(lambda rec: rec.state in {"completed", "cancelled", "no_show"}) and set(values) - {"message_follower_ids", "message_partner_ids"}:
            raise AccessError(_("Closed interview sessions are historical evidence and cannot be edited."))
        return super().write(values)

    @api.depends("score_ids.state", "score_ids.overall_score")
    def _compute_score_summary(self):
        for session in self:
            session.score_count = len(session.score_ids)
            finals = session.score_ids.filtered(lambda rec: rec.state == "final")
            session.finalized_score_count = len(finals)
            session.average_overall_score = sum(finals.mapped("overall_score")) / len(finals) if finals else 0.0

    @api.constrains("scheduled_start", "scheduled_end")
    def _check_schedule(self):
        for session in self:
            if session.scheduled_start and session.scheduled_end and session.scheduled_end <= session.scheduled_start:
                raise ValidationError(_("Interview end must be after interview start."))

    @api.constrains("applicant_id", "requisition_id", "company_id", "template_id")
    def _check_scope_alignment(self):
        for session in self:
            if session.applicant_id.company_id and session.applicant_id.company_id != session.company_id:
                raise ValidationError(_("Applicant and interview session must belong to the same company."))
            if session.requisition_id and session.requisition_id.company_id != session.company_id:
                raise ValidationError(_("Requisition and interview session must belong to the same company."))
            if session.requisition_id and session.applicant_id.onehr_requisition_id and session.requisition_id != session.applicant_id.onehr_requisition_id:
                raise ValidationError(_("Interview requisition must match the applicant requisition."))
            if session.template_id.company_id and session.template_id.company_id != session.company_id:
                raise ValidationError(_("Interview template company does not match the session company."))
            if session.template_id.job_id and session.template_id.job_id != session.applicant_id.job_id:
                raise ValidationError(_("Job-specific interview template does not match the applicant job."))

    def action_confirm(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "planned":
            raise UserError(_("Only planned interviews can be confirmed."))
        if not self.interviewer_user_ids:
            raise UserError(_("Assign at least one interviewer before confirming."))
        if self.lead_interviewer_user_id and self.lead_interviewer_user_id not in self.interviewer_user_ids:
            raise UserError(_("Lead interviewer must be included in Interviewers."))
        self.write({"state": "confirmed"})
        return True

    def action_schedule_calendar_event(self):
        self.ensure_one()
        require_recruiter(self)
        if self.calendar_event_id:
            return open_record_action(name=_("Interview Calendar Event"), res_model="calendar.event", res_id=self.calendar_event_id.id)
        partner_ids = self.interviewer_user_ids.mapped("partner_id").ids
        event = self.env["calendar.event"].create({
            "name": self.name,
            "start": self.scheduled_start,
            "stop": self.scheduled_end,
            "location": self.location,
            "partner_ids": [(6, 0, partner_ids)],
            "applicant_id": self.applicant_id.id,
        })
        self.write({"calendar_event_id": event.id})
        return open_record_action(name=_("Interview Calendar Event"), res_model="calendar.event", res_id=event.id)

    def action_create_my_scorecard(self):
        self.ensure_one()
        require_hiring_manager(self)
        if self.state not in {"confirmed", "completed"}:
            raise UserError(_("Scorecards may be recorded only for confirmed or completed interviews."))
        existing = self.score_ids.filtered(lambda score: score.rater_user_id == self.env.user and score.state in {"draft", "final"})[:1]
        if existing:
            return existing.action_open_self()
        score = self.env["onehr.interview.score"].create({
            "session_id": self.id,
            "rater_user_id": self.env.user.id,
        })
        return score.action_open_self()

    def action_complete(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state != "confirmed":
            raise UserError(_("Only confirmed interviews can be completed."))
        if not self.score_ids.filtered(lambda rec: rec.state == "final"):
            raise UserError(_("At least one finalized scorecard is required before completing the interview."))
        if not self.outcome:
            raise UserError(_("Set an interview outcome before completion."))
        self.write({"state": "completed", "completed_at": fields.Datetime.now()})
        return True

    def action_mark_no_show(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state not in {"planned", "confirmed"}:
            raise UserError(_("Only planned or confirmed interviews can be marked no-show."))
        self.write({"state": "no_show"})
        return True

    def action_cancel(self):
        self.ensure_one()
        require_recruiter(self)
        if self.state in {"completed", "cancelled", "no_show"}:
            raise UserError(_("This interview is already closed."))
        if not self.cancellation_reason:
            raise UserError(_("Enter a cancellation reason before cancelling."))
        self.write({"state": "cancelled"})
        return True

    def action_open_applicant(self):
        self.ensure_one()
        return open_record_action(name=_("Applicant"), res_model="hr.applicant", res_id=self.applicant_id.id)

    def action_open_calendar_event(self):
        self.ensure_one()
        if not self.calendar_event_id:
            raise UserError(_("No calendar event is linked to this interview."))
        return open_record_action(name=_("Calendar Event"), res_model="calendar.event", res_id=self.calendar_event_id.id)

    def action_open_scores(self):
        self.ensure_one()
        return open_records_action(
            name=_("Scorecards — %s", self.name), res_model="onehr.interview.score",
            domain=[("session_id", "=", self.id)], context={"default_session_id": self.id},
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        if any(rec.state != "planned" or rec.score_ids for rec in self):
            raise UserError(_("Only unused planned interview sessions may be deleted."))


class OneHRInterviewScore(models.Model):
    """Per-rater scorecard evidence; finalized records are immutable (ED3)."""

    _name = "onehr.interview.score"
    _description = "OneHR Interview Score"
    _inherit = ["onehr.mixin.audit"]
    _order = "session_id desc, id desc"

    name = fields.Char(compute="_compute_name", store=True, index=True)
    session_id = fields.Many2one(
        "onehr.interview.session", required=True, index=True, tracking=True, ondelete="restrict", check_company=True
    )
    company_id = fields.Many2one(related="session_id.company_id", store=True, index=True, readonly=True)
    applicant_id = fields.Many2one(related="session_id.applicant_id", store=True, index=True, readonly=True)
    template_id = fields.Many2one(related="session_id.template_id", store=True, index=True, readonly=True)
    rater_user_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user,
        index=True, tracking=True, ondelete="restrict"
    )
    scorecard_values = fields.Properties(
        string="Scorecard",
        definition="session_id.template_id.scorecard_definition",
    )
    overall_score = fields.Float(required=True, default=0.0, tracking=True)
    recommendation = fields.Selection(
        [("strong_yes", "Strong Yes"), ("yes", "Yes"), ("hold", "Hold"), ("no", "No"), ("strong_no", "Strong No")],
        tracking=True,
    )
    strengths = fields.Text()
    concerns = fields.Text()
    comments = fields.Text()
    state = fields.Selection(
        [("draft", "Draft"), ("final", "Final"), ("superseded", "Superseded")],
        required=True, default="draft", index=True, tracking=True, copy=False,
    )
    finalized_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    supersedes_id = fields.Many2one("onehr.interview.score", readonly=True, copy=False, ondelete="restrict")
    superseded_by_id = fields.Many2one("onehr.interview.score", readonly=True, copy=False, ondelete="restrict")

    @api.depends("session_id.name", "rater_user_id.name")
    def _compute_name(self):
        for score in self:
            score.name = _("%s — %s", score.session_id.name or _("Interview"), score.rater_user_id.name or _("Rater"))

    @api.model_create_multi
    def create(self, vals_list):
        require_hiring_manager(self)
        for values in vals_list:
            session = self.env["onehr.interview.session"].browse(values.get("session_id"))
            rater = self.env["res.users"].browse(values.get("rater_user_id") or self.env.user.id)
            if session and rater not in session.interviewer_user_ids and not self.env.user.has_group("onehr_recruitment.group_onehr_recruitment_manager"):
                raise AccessError(_("Only assigned interviewers may create scorecards for this session."))
        return super().create(vals_list)

    def write(self, values):
        require_hiring_manager(self)
        if self.filtered(lambda rec: rec.state in {"final", "superseded"}):
            raise AccessError(_("Finalized or superseded scorecards are immutable. Create a correction instead."))
        if any(rec.rater_user_id != self.env.user for rec in self) and not self.env.user.has_group("onehr_recruitment.group_onehr_recruitment_manager"):
            raise AccessError(_("Only the scorecard rater or Recruitment Manager may edit this draft."))
        return super().write(values)

    @api.constrains("overall_score")
    def _check_overall_score(self):
        for score in self:
            if not 0.0 <= score.overall_score <= 5.0:
                raise ValidationError(_("Overall interview score must be between 0 and 5."))

    @api.constrains("session_id", "rater_user_id", "state")
    def _check_single_current_score(self):
        for score in self.filtered(lambda rec: rec.state in {"draft", "final"}):
            if self.search_count([
                ("id", "!=", score.id),
                ("session_id", "=", score.session_id.id),
                ("rater_user_id", "=", score.rater_user_id.id),
                ("state", "in", ["draft", "final"]),
            ]):
                raise ValidationError(_("A rater may have only one current scorecard per interview session."))

    def action_finalize(self):
        self.ensure_one()
        require_hiring_manager(self)
        if self.state != "draft":
            raise UserError(_("Only draft scorecards can be finalized."))
        if self.rater_user_id != self.env.user and not self.env.user.has_group("onehr_recruitment.group_onehr_recruitment_manager"):
            raise AccessError(_("Only the scorecard rater or Recruitment Manager may finalize it."))
        if not self.recommendation:
            raise UserError(_("Select a recommendation before finalizing the scorecard."))
        super(OneHRInterviewScore, self).write({"state": "final", "finalized_at": fields.Datetime.now()})
        return True

    def action_create_correction(self):
        self.ensure_one()
        require_recruitment_manager(self)
        if self.state != "final":
            raise UserError(_("Only a final scorecard can be corrected."))
        # Supersede first so the unique-current constraint permits the correction.
        # If copy fails, the surrounding transaction rolls this state change back.
        super(OneHRInterviewScore, self).write({"state": "superseded"})
        correction = self.copy({
            "state": "draft",
            "finalized_at": False,
            "supersedes_id": self.id,
            "superseded_by_id": False,
        })
        super(OneHRInterviewScore, self).write({"superseded_by_id": correction.id})
        return correction.action_open_self()

    def action_open_self(self):
        self.ensure_one()
        return open_record_action(name=_("Interview Scorecard"), res_model=self._name, res_id=self.id)

    def action_open_session(self):
        self.ensure_one()
        return open_record_action(name=_("Interview Session"), res_model="onehr.interview.session", res_id=self.session_id.id)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        if any(rec.state != "draft" for rec in self):
            raise UserError(_("Only draft scorecards may be deleted. Final evidence must be retained."))

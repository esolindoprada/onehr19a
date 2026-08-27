from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    is_appraisal_hr,
    is_appraisal_manager,
    require_appraisal_admin,
    require_appraisal_hr,
)


class OneHRAppraisalForm(models.Model):
    _name = "onehr.appraisal.form"
    _description = "OneHR Appraisal Form"
    _inherit = ["onehr.mixin.audit"]
    _order = "cycle_id desc, employee_id, id"

    _cycle_employee_unique = models.Constraint(
        "UNIQUE(cycle_id, employee_id)",
        "An employee can have only one appraisal form in the same cycle.",
    )

    _ACTION_CONTEXT = "onehr_appraisal_action_write"

    name = fields.Char(
        string="Appraisal Reference", required=True, default="New",
        copy=False, readonly=True, tracking=True, index=True,
    )
    cycle_id = fields.Many2one(
        "onehr.appraisal.cycle", required=True, ondelete="restrict",
        index=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", related="cycle_id.company_id", store=True, index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    employee_name = fields.Char(
        related="employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    employee_number = fields.Char(
        related="employee_id.onehr_employee_number",
        store=True,
        compute_sudo=True,
        index=True,
        readonly=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    employee_user_id = fields.Many2one(
        "res.users",
        related="employee_id.user_id",
        store=True,
        readonly=True,
        index=True,
    )
    manager_employee_id = fields.Many2one(
        "hr.employee",
        string="Appraising Manager",
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    manager_name = fields.Char(
        related="manager_employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    manager_user_id = fields.Many2one(
        "res.users",
        related="manager_employee_id.user_id",
        store=True,
        readonly=True,
        index=True,
    )
    department_id = fields.Many2one(
        "hr.department",
        related="employee_id.department_id",
        store=True,
        compute_sudo=True,
        index=True,
        readonly=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    department_name = fields.Char(
        related="employee_id.department_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    job_id = fields.Many2one(
        "hr.job",
        related="employee_id.job_id",
        store=True,
        compute_sudo=True,
        index=True,
        readonly=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    job_name = fields.Char(
        related="employee_id.job_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    grade_id = fields.Many2one(
        "onehr.grade",
        related="employee_id.onehr_grade_id",
        store=True,
        compute_sudo=True,
        index=True,
        readonly=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    grade_name = fields.Char(
        related="employee_id.onehr_grade_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    peer_reviewer_ids = fields.Many2many(
        "hr.employee",
        "onehr_appraisal_form_peer_reviewer_rel",
        "form_id", "employee_id",
        string="Peer Reviewers",
        check_company=True,
        tracking=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    peer_reviewer_names = fields.Char(
        string="Peer Reviewers",
        compute="_compute_peer_reviewer_names",
        store=True,
        compute_sudo=True,
        readonly=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("consolidation", "Consolidation"),
            ("closed", "Closed"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", required=True, tracking=True, index=True,
    )
    self_review_state = fields.Selection(
        [("not_required", "Not Required"), ("pending", "Pending"), ("done", "Done")],
        default="pending", required=True, tracking=True,
    )
    manager_review_state = fields.Selection(
        [("not_required", "Not Required"), ("pending", "Pending"), ("done", "Done")],
        default="pending", required=True, tracking=True,
    )
    peer_review_state = fields.Selection(
        [
            ("not_required", "Not Required"),
            ("not_requested", "Not Requested"),
            ("requested", "Requested"),
            ("partial", "Partial"),
            ("done", "Done"),
        ],
        default="not_requested", required=True, tracking=True,
    )
    self_weight = fields.Float(
        related="cycle_id.self_weight", store=True, readonly=True,
    )
    manager_weight = fields.Float(
        related="cycle_id.manager_weight", store=True, readonly=True,
    )
    peer_weight = fields.Float(
        related="cycle_id.peer_weight", store=True, readonly=True,
    )

    review_started_at = fields.Datetime(readonly=True, tracking=True)
    self_submitted_at = fields.Datetime(readonly=True, tracking=True)
    manager_submitted_at = fields.Datetime(readonly=True, tracking=True)
    consolidation_at = fields.Datetime(readonly=True, tracking=True)
    closed_at = fields.Datetime(readonly=True, tracking=True)
    retention_until = fields.Date(
        compute="_compute_retention_until",
        store=True,
        readonly=True,
        index=True,
    )

    employee_achievements = fields.Html(tracking=True)
    employee_challenges = fields.Html(tracking=True)
    employee_comments = fields.Html(tracking=True)
    manager_summary = fields.Html(tracking=True)
    strengths = fields.Html(tracking=True)
    improvement_areas = fields.Html(tracking=True)
    final_comments = fields.Html(tracking=True)

    development_plan = fields.Html(tracking=True)
    development_due_date = fields.Date(tracking=True)

    score_ids = fields.One2many(
        "onehr.appraisal.score", "form_id",
        string="Scores / Objectives / Development",
        domain=[("is_template", "=", False)],
    )
    objective_ids = fields.One2many(
        "onehr.appraisal.score",
        "form_id",
        string="Objectives / KPIs",
        domain=[
            ("is_template", "=", False),
            ("parent_score_id", "=", False),
            ("line_type", "!=", "development"),
        ],
    )
    development_action_ids = fields.One2many(
        "onehr.appraisal.score",
        "form_id",
        string="Development Actions",
        domain=[
            ("is_template", "=", False),
            ("line_type", "=", "development"),
        ],
    )
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_appraisal_form_attachment_rel",
        "form_id", "attachment_id",
        string="Evidence Attachments",
        copy=False,
    )

    self_score = fields.Float(compute="_compute_scores", store=True)
    manager_score = fields.Float(compute="_compute_scores", store=True)
    peer_score = fields.Float(compute="_compute_scores", store=True)
    overall_score = fields.Float(compute="_compute_scores", store=True)
    potential_score = fields.Float(
        string="Potential Score", tracking=True,
        help="Optional calibration input for downstream talent/succession analysis.",
    )
    final_score = fields.Float(tracking=True)
    final_rating_label = fields.Selection(
        [
            ("below", "Below Expectations"),
            ("partial", "Partially Meets"),
            ("meets", "Meets Expectations"),
            ("exceeds", "Exceeds Expectations"),
            ("outstanding", "Outstanding"),
        ],
        compute="_compute_final_rating", store=True, index=True,
    )
    nine_box_position = fields.Selection(
        [
            ("low_low", "Low Performance / Low Potential"),
            ("low_mid", "Low Performance / Medium Potential"),
            ("low_high", "Low Performance / High Potential"),
            ("mid_low", "Medium Performance / Low Potential"),
            ("mid_mid", "Medium Performance / Medium Potential"),
            ("mid_high", "Medium Performance / High Potential"),
            ("high_low", "High Performance / Low Potential"),
            ("high_mid", "High Performance / Medium Potential"),
            ("high_high", "High Performance / High Potential"),
        ],
        compute="_compute_nine_box", store=True, index=True,
    )

    employee_acknowledged = fields.Boolean(readonly=True, tracking=True)
    acknowledged_at = fields.Datetime(readonly=True, tracking=True)
    acknowledgement_comment = fields.Text(tracking=True)

    objective_count = fields.Integer(compute="_compute_counts")
    peer_feedback_count = fields.Integer(compute="_compute_counts")
    development_count = fields.Integer(compute="_compute_counts")
    submitted_rating_count = fields.Integer(compute="_compute_counts")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                vals["name"] = self.env["ir.sequence"].next_by_code(
                    "onehr.appraisal.form"
                ) or "New"
            cycle = self.env["onehr.appraisal.cycle"].browse(vals.get("cycle_id"))
            if cycle:
                vals.setdefault(
                    "self_review_state",
                    "not_required" if cycle.self_weight <= 0 else "pending",
                )
                vals.setdefault(
                    "manager_review_state",
                    "not_required" if cycle.manager_weight <= 0 else "pending",
                )
                vals.setdefault(
                    "peer_review_state",
                    "not_required" if cycle.peer_weight <= 0 else "not_requested",
                )
            employee = self.env["hr.employee"].browse(vals.get("employee_id"))
            if employee and not vals.get("manager_employee_id"):
                vals["manager_employee_id"] = employee.parent_id.id or False
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get(self._ACTION_CONTEXT):
            return super().write(vals)

        immutable_after_create = {"cycle_id", "employee_id"}
        if immutable_after_create.intersection(vals):
            raise AccessError(
                _("Appraisal Cycle and Employee ownership are immutable after creation.")
            )
        for form in self:
            if (
                "manager_employee_id" in vals
                and form.state not in ("draft", "in_review")
            ):
                raise AccessError(
                    _("Appraising Manager cannot be reassigned after Consolidation starts.")
                )
            if (
                "peer_reviewer_ids" in vals
                and form.state not in ("draft", "in_review")
            ):
                raise AccessError(
                    _("Peer Reviewers can be assigned only before Consolidation.")
                )

        lifecycle_protected = {
            "name", "state", "self_review_state", "manager_review_state",
            "peer_review_state", "review_started_at", "self_submitted_at",
            "manager_submitted_at", "consolidation_at", "closed_at",
            "self_score", "manager_score", "peer_score", "overall_score",
            "final_rating_label", "nine_box_position",
            "employee_acknowledged", "acknowledged_at",
        }
        if lifecycle_protected.intersection(vals):
            raise AccessError(
                _("Lifecycle and calculated fields must change through governed actions.")
            )

        # Appraisal HR may maintain business ownership/configuration fields, but the
        # lifecycle above remains action-controlled for every role.
        if is_appraisal_hr(self.env):
            return super().write(vals)

        manager_allowed = {
            "manager_summary", "strengths",
            "improvement_areas", "final_comments", "development_plan",
            "development_due_date", "potential_score", "final_score",
            "evidence_attachment_ids", "message_follower_ids",
        }
        participant_allowed = {
            "employee_achievements", "employee_challenges", "employee_comments",
            "acknowledgement_comment", "evidence_attachment_ids", "message_follower_ids",
        }

        # A user may legitimately hold both Manager and Participant. Authority is
        # determined against each form, so a manager can still complete their own
        # appraisal without gaining manager authority over unrelated records.
        requested = set(vals)
        for appraisal in self:
            allowed = set()
            if (
                is_appraisal_manager(self.env)
                and appraisal.manager_user_id == self.env.user
            ):
                if appraisal.state not in ("in_review", "consolidation"):
                    raise AccessError(
                        _("Manager review content is editable only during Review/Consolidation.")
                    )
                allowed |= manager_allowed
            if appraisal.employee_user_id == self.env.user:
                employee_narrative = {
                    "employee_achievements", "employee_challenges",
                    "employee_comments", "evidence_attachment_ids",
                    "message_follower_ids",
                }
                acknowledgement = {"acknowledgement_comment"}
                if requested & employee_narrative and appraisal.state not in ("draft", "in_review"):
                    raise AccessError(
                        _("Employee review narrative/evidence is frozen after Review.")
                    )
                if (
                    requested & acknowledgement
                    and (
                        appraisal.state not in ("consolidation", "closed")
                        or appraisal.employee_acknowledged
                    )
                ):
                    raise AccessError(
                        _("Acknowledgement comments are editable only before acknowledgement.")
                    )
                allowed |= participant_allowed
            if not allowed:
                raise AccessError(
                    _("You are not authorized to update this appraisal form.")
                )
            if requested - allowed:
                raise AccessError(
                    _("The requested fields exceed your authority on this appraisal form.")
                )
        return super().write(vals)

    @api.depends("cycle_id.date_end", "cycle_id.retention_years")
    def _compute_retention_until(self):
        from dateutil.relativedelta import relativedelta

        for form in self:
            form.retention_until = (
                form.cycle_id.date_end
                + relativedelta(years=form.cycle_id.retention_years)
                if form.cycle_id.date_end
                else False
            )

    @api.depends("peer_reviewer_ids.name")
    def _compute_peer_reviewer_names(self):
        for form in self:
            form.peer_reviewer_names = ", ".join(
                form.peer_reviewer_ids.sorted("name").mapped("name")
            )

    @api.depends(
        "score_ids.rating", "score_ids.rating_state", "score_ids.rater_type",
        "score_ids.weight", "score_ids.parent_score_id",
        "cycle_id.self_weight", "cycle_id.manager_weight", "cycle_id.peer_weight",
    )
    def _compute_scores(self):
        for form in self:
            submitted = form.score_ids.filtered(
                lambda line: (
                    not line.is_template
                    and line.parent_score_id
                    and line.rating_state == "submitted"
                    and line.rater_type in ("self", "manager", "peer")
                )
            )
            category_scores = {}
            for rater_type in ("self", "manager", "peer"):
                lines = submitted.filtered(lambda line: line.rater_type == rater_type)
                total_weight = sum(lines.mapped("weight"))
                category_scores[rater_type] = (
                    sum(line.normalized_score * line.weight for line in lines) / total_weight
                    if total_weight else 0.0
                )

            form.self_score = category_scores["self"]
            form.manager_score = category_scores["manager"]
            form.peer_score = category_scores["peer"]

            configured = {
                "self": form.cycle_id.self_weight,
                "manager": form.cycle_id.manager_weight,
                "peer": form.cycle_id.peer_weight,
            }
            available = {
                rater: configured[rater]
                for rater in ("self", "manager", "peer")
                if submitted.filtered(lambda line, r=rater: line.rater_type == r)
                and configured[rater] > 0
            }
            weight_total = sum(available.values())
            form.overall_score = (
                sum(category_scores[rater] * weight for rater, weight in available.items())
                / weight_total
                if weight_total else 0.0
            )

    @api.depends("final_score")
    def _compute_final_rating(self):
        for form in self:
            score = form.final_score
            if score <= 0:
                form.final_rating_label = False
            elif score < 50:
                form.final_rating_label = "below"
            elif score < 65:
                form.final_rating_label = "partial"
            elif score < 80:
                form.final_rating_label = "meets"
            elif score < 90:
                form.final_rating_label = "exceeds"
            else:
                form.final_rating_label = "outstanding"

    @api.depends("final_score", "potential_score")
    def _compute_nine_box(self):
        def band(value):
            if value <= 0:
                return False
            if value < 65:
                return "low"
            if value < 85:
                return "mid"
            return "high"

        for form in self:
            performance = band(form.final_score)
            potential = band(form.potential_score)
            form.nine_box_position = (
                f"{performance}_{potential}" if performance and potential else False
            )

    @api.depends(
        "score_ids.line_type", "score_ids.rater_type",
        "score_ids.rating_state", "score_ids.parent_score_id",
    )
    def _compute_counts(self):
        for form in self:
            lines = form.score_ids
            form.objective_count = len(lines.filtered(
                lambda line: not line.parent_score_id and line.line_type != "development"
            ))
            form.peer_feedback_count = len(lines.filtered(
                lambda line: line.rater_type == "peer"
            ))
            form.development_count = len(lines.filtered(
                lambda line: line.line_type == "development"
            ))
            form.submitted_rating_count = len(lines.filtered(
                lambda line: line.rating_state == "submitted"
            ))

    @api.constrains("cycle_id", "employee_id", "manager_employee_id", "peer_reviewer_ids")
    def _check_company_alignment(self):
        for form in self:
            if form.employee_id.company_id != form.company_id:
                raise ValidationError(_("Employee and appraisal cycle must belong to the same company."))
            if form.manager_employee_id and form.manager_employee_id.company_id != form.company_id:
                raise ValidationError(_("Appraising Manager must belong to the appraisal company."))
            if any(peer.company_id != form.company_id for peer in form.peer_reviewer_ids):
                raise ValidationError(_("Every Peer Reviewer must belong to the appraisal company."))

    @api.constrains("potential_score", "final_score")
    def _check_calibration_scores(self):
        for form in self:
            for value, label in (
                (form.potential_score, _("Potential Score")),
                (form.final_score, _("Final Score")),
            ):
                if value < 0 or value > 100:
                    raise ValidationError(_("%s must be between 0 and 100.") % label)

    def _is_employee_user(self):
        self.ensure_one()
        return self.employee_user_id == self.env.user

    def _is_manager_user(self):
        self.ensure_one()
        return self.manager_user_id == self.env.user

    def _require_employee(self):
        self.ensure_one()
        if not self._is_employee_user():
            raise AccessError(_("Only the appraised employee may perform this action."))

    def _require_manager_or_hr_for_form(self):
        self.ensure_one()
        if is_appraisal_hr(self.env):
            return
        if not is_appraisal_manager(self.env) or not self._is_manager_user():
            raise AccessError(_("Only the assigned manager or Appraisal HR may perform this action."))

    def _action_write(self, values):
        return self.with_context(**{self._ACTION_CONTEXT: True}).write(values)

    def action_start_review(self):
        for form in self:
            form._require_manager_or_hr_for_form()
            if form.state != "draft":
                raise UserError(_("Only a Draft appraisal can start review."))
            if form.cycle_id.state != "in_review":
                raise UserError(_("HR must open the appraisal cycle before a review can start."))
            form._action_write({
                "state": "in_review",
                "review_started_at": fields.Datetime.now(),
            })
        return display_notification(_("Appraisal review started."))

    def action_submit_self_review(self):
        for form in self:
            form._require_employee()
            if form.state != "in_review":
                raise UserError(_("Self review can only be submitted while In Review."))
            if form.self_weight <= 0:
                raise UserError(_("Self review is not required by this cycle's rater configuration."))
            lines = form.score_ids.filtered(lambda line: line.rater_type == "self")
            if not lines:
                raise UserError(_("No Self rating lines are available."))
            if lines.filtered(lambda line: not line.rating):
                raise UserError(_("Complete every Self rating before submitting."))
            lines.with_context(onehr_appraisal_score_action=True).write(
                {"rating_state": "submitted"}
            )
            form._action_write({
                "self_review_state": "done",
                "self_submitted_at": fields.Datetime.now(),
            })
        return display_notification(_("Self review submitted."))

    def action_request_peer_feedback(self):
        require_appraisal_hr(self)
        created_count = 0
        Score = self.env["onehr.appraisal.score"]
        for form in self:
            if form.state != "in_review":
                raise UserError(_("Peer feedback can only be requested while In Review."))
            if form.peer_weight <= 0:
                raise UserError(_("Peer review is disabled by this cycle's rater configuration."))
            if not form.peer_reviewer_ids:
                raise UserError(_("Select at least one Peer Reviewer first."))

            targets = form.score_ids.filtered(
                lambda line: not line.parent_score_id
                and line.line_type != "development"
                and line.rater_type == "target"
            )
            for reviewer in form.peer_reviewer_ids:
                for target in targets:
                    existing = Score.search([
                        ("form_id", "=", form.id),
                        ("parent_score_id", "=", target.id),
                        ("rater_type", "=", "peer"),
                        ("reviewer_employee_id", "=", reviewer.id),
                    ], limit=1)
                    if existing:
                        continue
                    Score.create({
                        "cycle_id": form.cycle_id.id,
                        "form_id": form.id,
                        "parent_score_id": target.id,
                        "line_type": target.line_type,
                        "item_code": target.item_code,
                        "title": target.title,
                        "weight": target.weight,
                        "rater_type": "peer",
                        "reviewer_employee_id": reviewer.id,
                    })
                    created_count += 1

                if reviewer.user_id:
                    form.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=reviewer.user_id.id,
                        summary=_("Peer appraisal feedback requested"),
                        note=_("Provide peer feedback for %s.") % form.employee_name,
                    )
            form._action_write({"peer_review_state": "requested"})
        return display_notification(
            _("Peer feedback requested; %s rating line(s) created.") % created_count
        )

    def _refresh_peer_state(self):
        for form in self:
            peer_lines = form.score_ids.filtered(lambda line: line.rater_type == "peer")
            if form.peer_weight <= 0:
                state = "not_required"
            elif not peer_lines:
                state = "not_requested"
            else:
                submitted = peer_lines.filtered(lambda line: line.rating_state == "submitted")
                if not submitted:
                    state = "requested"
                elif len(submitted) < len(peer_lines):
                    state = "partial"
                else:
                    state = "done"
            form._action_write({"peer_review_state": state})

    def action_submit_manager_review(self):
        for form in self:
            form._require_manager_or_hr_for_form()
            if form.state != "in_review":
                raise UserError(_("Manager review can only be submitted while In Review."))
            if form.manager_weight <= 0:
                raise UserError(_("Manager review is not required by this cycle's rater configuration."))
            lines = form.score_ids.filtered(lambda line: line.rater_type == "manager")
            if not lines:
                raise UserError(_("No Manager rating lines are available."))
            if lines.filtered(lambda line: not line.rating):
                raise UserError(_("Complete every Manager rating before submitting."))
            lines.with_context(onehr_appraisal_score_action=True).write(
                {"rating_state": "submitted"}
            )
            form._action_write({
                "manager_review_state": "done",
                "manager_submitted_at": fields.Datetime.now(),
            })
        return display_notification(_("Manager review submitted."))

    def action_move_to_consolidation(self):
        for form in self:
            form._require_manager_or_hr_for_form()
            if form.state != "in_review":
                raise UserError(_("Only an In Review form can enter Consolidation."))
            if form.self_weight > 0 and form.self_review_state != "done":
                raise UserError(_("Self review must be completed before Consolidation."))
            if form.manager_weight > 0 and form.manager_review_state != "done":
                raise UserError(_("Manager review must be completed before Consolidation."))
            form._refresh_peer_state()
            if form.peer_weight > 0 and form.peer_review_state != "done":
                raise UserError(
                    _("All configured Peer feedback must be submitted before Consolidation.")
                )
            form._action_write({
                "state": "consolidation",
                "consolidation_at": fields.Datetime.now(),
                "final_score": form.overall_score,
            })
        return display_notification(_("Appraisal moved to Consolidation."))

    def action_recalculate_score(self):
        for form in self:
            form.check_access("read")
            if form.state == "consolidation" and (
                form._is_manager_user() or is_appraisal_hr(self.env)
            ):
                form._action_write({"final_score": form.overall_score})
        return display_notification(_("Calculated scores refreshed from submitted ratings."))

    def action_acknowledge(self):
        for form in self:
            form._require_employee()
            if form.state not in ("consolidation", "closed"):
                raise UserError(_("Acknowledgement is available only after Consolidation."))
            form._action_write({
                "employee_acknowledged": True,
                "acknowledged_at": fields.Datetime.now(),
            })
        return display_notification(_("Appraisal acknowledged."))

    def action_close(self):
        require_appraisal_hr(self)
        for form in self:
            if form.state != "consolidation":
                raise UserError(_("Only a Consolidation appraisal can be closed."))
            if form.final_score <= 0:
                raise UserError(_("A Final Score is required before closing."))
            form._action_write({
                "state": "closed",
                "closed_at": fields.Datetime.now(),
            })
        return display_notification(_("Appraisal closed and retained as performance evidence."))

    def action_cancel(self):
        require_appraisal_hr(self)
        for form in self:
            if form.state == "closed":
                raise UserError(_("A closed appraisal cannot be cancelled."))
            form._action_write({"state": "cancelled"})
        return display_notification(_("Appraisal cancelled."), notification_type="warning")

    def action_reset_draft(self):
        require_appraisal_admin(self)
        for form in self:
            if form.score_ids.filtered(lambda line: line.rating_state == "submitted"):
                raise UserError(_("Reset is blocked because submitted rating evidence exists."))
            form._action_write({
                "state": "draft",
                "self_review_state": "pending",
                "manager_review_state": "pending",
                "peer_review_state": "not_requested",
                "review_started_at": False,
                "self_submitted_at": False,
                "manager_submitted_at": False,
                "consolidation_at": False,
                "closed_at": False,
                "final_score": 0.0,
            })
        return display_notification(_("Appraisal reset to Draft."))

    def action_print_appraisal(self):
        self.ensure_one()
        return self.env.ref(
            "onehr_appraisal.action_report_onehr_appraisal"
        ).report_action(self)

    def _score_action(self, domain, name):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": name,
            "res_model": "onehr.appraisal.score",
            "view_mode": "list,form,pivot,graph",
            "domain": [("form_id", "=", self.id)] + domain,
            "context": {
                "default_cycle_id": self.cycle_id.id,
                "default_form_id": self.id,
                "default_is_template": False,
            },
        }

    def action_open_objectives(self):
        return self._score_action(
            [("parent_score_id", "=", False), ("line_type", "!=", "development")],
            _("Objectives / KPIs"),
        )

    def action_open_peer_feedback(self):
        return self._score_action([("rater_type", "=", "peer")], _("Peer Feedback"))

    def action_open_development(self):
        return self._score_action(
            [("line_type", "=", "development")],
            _("Development Plan Actions"),
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unstarted(self):
        for form in self:
            if form.state not in ("draft", "cancelled"):
                raise UserError(
                    _("Started/closed appraisal evidence cannot be deleted; cancel it instead.")
                )
            if form.score_ids.filtered(lambda line: line.rating_state == "submitted"):
                raise UserError(
                    _("Appraisal evidence with submitted ratings cannot be deleted.")
                )

    @api.model
    def _cron_appraisal_deadline_reminders(self):
        today = fields.Date.context_today(self)
        forms = self.search([
            ("state", "=", "in_review"),
            ("company_id", "in", self.env.companies.ids),
        ])
        todo_type = self.env.ref("mail.mail_activity_data_todo")
        for form in forms:
            reminders = [
                (
                    form.cycle_id.self_review_deadline,
                    form.employee_user_id,
                    _("Self appraisal deadline"),
                ),
                (
                    form.cycle_id.manager_review_deadline,
                    form.manager_user_id,
                    _("Manager appraisal deadline"),
                ),
            ]
            for deadline, user, summary in reminders:
                if not deadline or not user:
                    continue
                if 0 <= (deadline - today).days <= 3:
                    duplicate = form.activity_ids.filtered(
                        lambda activity: (
                            activity.activity_type_id == todo_type
                            and activity.user_id == user
                            and activity.date_deadline == deadline
                        )
                    )
                    if not duplicate:
                        form.activity_schedule(
                            todo_type.id,
                            user_id=user.id,
                            date_deadline=deadline,
                            summary=summary,
                        )

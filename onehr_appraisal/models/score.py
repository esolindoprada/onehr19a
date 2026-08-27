from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    is_appraisal_hr,
    is_appraisal_manager,
    require_appraisal_hr,
)


class OneHRAppraisalScore(models.Model):
    _name = "onehr.appraisal.score"
    _description = "OneHR Appraisal Score / Objective / Development Line"
    _inherit = ["onehr.mixin.audit"]
    _order = "is_template desc, sequence, id"

    sequence = fields.Integer(default=10, index=True)
    cycle_id = fields.Many2one(
        "onehr.appraisal.cycle", required=True, ondelete="cascade",
        index=True, tracking=True,
    )
    form_id = fields.Many2one(
        "onehr.appraisal.form", ondelete="cascade", index=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", related="cycle_id.company_id", store=True, index=True,
    )
    employee_id = fields.Many2one(
        "hr.employee",
        related="form_id.employee_id",
        store=True,
        compute_sudo=True,
        index=True,
        readonly=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    employee_name = fields.Char(
        related="form_id.employee_name",
        store=True,
        readonly=True,
        index=True,
    )
    employee_user_id = fields.Many2one(
        "res.users",
        related="form_id.employee_user_id",
        store=True,
        readonly=True,
        index=True,
    )
    manager_user_id = fields.Many2one(
        "res.users",
        related="form_id.manager_user_id",
        store=True,
        readonly=True,
        index=True,
    )
    form_reference = fields.Char(
        related="form_id.name",
        store=True,
        readonly=True,
        index=True,
    )
    grade_name = fields.Char(
        related="form_id.grade_name",
        store=True,
        readonly=True,
        index=True,
    )
    is_template = fields.Boolean(default=False, index=True, tracking=True)
    parent_score_id = fields.Many2one(
        "onehr.appraisal.score", string="Target / Objective",
        ondelete="cascade", index=True,
    )
    parent_item_code = fields.Char(
        related="parent_score_id.item_code",
        store=True,
        readonly=True,
        index=True,
    )
    parent_title = fields.Char(
        related="parent_score_id.title",
        store=True,
        compute_sudo=True,
        readonly=True,
    )
    rating_line_ids = fields.One2many(
        "onehr.appraisal.score", "parent_score_id",
        string="Multi-rater Feedback",
    )

    line_type = fields.Selection(
        [
            ("objective", "Objective / OKR"),
            ("kpi", "KPI"),
            ("competency", "Competency Evidence"),
            ("behavior", "Behavior"),
            ("feedback", "Feedback"),
            ("development", "Development Action"),
        ],
        default="objective", required=True, tracking=True, index=True,
    )
    item_code = fields.Char(index=True, tracking=True)
    title = fields.Char(required=True, tracking=True, index=True)
    description = fields.Text()
    weight = fields.Float(default=0.0, tracking=True)

    target_value = fields.Float(tracking=True)
    actual_value = fields.Float(tracking=True)
    achievement_percent = fields.Float(
        compute="_compute_achievement", store=True, string="Achievement %",
    )

    rater_type = fields.Selection(
        [
            ("target", "Target / Template"),
            ("self", "Self"),
            ("manager", "Manager"),
            ("peer", "Peer"),
            ("hr", "HR / Calibration"),
        ],
        default="target", required=True, tracking=True, index=True,
    )
    reviewer_employee_id = fields.Many2one(
        "hr.employee",
        ondelete="restrict",
        index=True,
        tracking=True,
        check_company=True,
        groups="onehr_appraisal.group_onehr_appraisal_hr",
    )
    reviewer_name = fields.Char(
        related="reviewer_employee_id.name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    reviewer_user_id = fields.Many2one(
        "res.users",
        related="reviewer_employee_id.user_id",
        store=True,
        readonly=True,
        index=True,
    )
    reviewer_company_id = fields.Many2one(
        "res.company",
        related="reviewer_employee_id.company_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )
    rating = fields.Float(tracking=True)
    normalized_score = fields.Float(
        compute="_compute_normalized_score", store=True, string="Normalized %",
    )
    weighted_score = fields.Float(
        compute="_compute_normalized_score", store=True, string="Weighted Score",
    )
    rating_state = fields.Selection(
        [("draft", "Draft"), ("submitted", "Submitted")],
        default="draft", required=True, tracking=True, index=True,
    )
    comments = fields.Text(tracking=True)

    development_state = fields.Selection(
        [
            ("draft", "Draft"),
            ("planned", "Planned"),
            ("in_progress", "In Progress"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="draft", tracking=True, index=True,
    )
    development_due_date = fields.Date(tracking=True)
    development_note = fields.Text(tracking=True)
    learning_session_reference = fields.Char(
        help="Exact OneHR Learning Session reference for governed IDP enrollment hand-off."
    )
    learning_reference = fields.Char(readonly=True, copy=False)
    evidence_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_appraisal_score_attachment_rel",
        "score_id", "attachment_id",
        string="Evidence Attachments",
        copy=False,
    )

    @api.model_create_multi
    def create(self, vals_list):
        if not is_appraisal_hr(self.env):
            for vals in vals_list:
                form = self.env["onehr.appraisal.form"].browse(vals.get("form_id"))
                if not form:
                    raise AccessError(_("Only Appraisal HR may create cycle template lines."))

                rater_type = vals.get("rater_type", "target")
                if (
                    is_appraisal_manager(self.env)
                    and form.manager_user_id == self.env.user
                ):
                    if rater_type not in ("manager", "peer"):
                        raise AccessError(
                            _("Appraisal Managers may create Manager/Peer feedback lines only.")
                        )
                    continue

                reviewer = self.env["hr.employee"].browse(vals.get("reviewer_employee_id"))
                own_employee = form.employee_user_id == self.env.user
                own_peer = bool(reviewer and reviewer.user_id == self.env.user)
                if not (
                    (rater_type == "self" and own_employee)
                    or (rater_type == "peer" and own_peer)
                ):
                    raise AccessError(
                        _("Participants may create only their own Self/Peer feedback lines.")
                    )
        return super().create(vals_list)

    def write(self, vals):
        if self.env.context.get("onehr_appraisal_score_action"):
            return super().write(vals)

        template_definition_fields = {
            "item_code", "title", "description", "weight",
            "target_value", "line_type", "rater_type",
        }
        for line in self:
            if (
                line.is_template
                and line.cycle_id.state != "draft"
                and template_definition_fields.intersection(vals)
            ):
                raise AccessError(
                    _("Cycle target templates are frozen after the cycle leaves Draft.")
                )

        # Appraisal HR is the governed correction authority after template-freeze.
        if is_appraisal_hr(self.env):
            return super().write(vals)

        lifecycle_fields = {
            "cycle_id", "form_id", "company_id", "employee_id",
            "is_template", "parent_score_id", "rater_type",
            "reviewer_employee_id", "rating_state", "learning_reference",
        }
        if lifecycle_fields.intersection(vals):
            raise AccessError(
                _("Ownership/rater/lifecycle fields must change through governed actions.")
            )

        target_allowed = {
            "actual_value", "comments", "evidence_attachment_ids",
            "message_follower_ids",
        }
        rating_allowed = {
            "rating", "comments", "evidence_attachment_ids",
            "message_follower_ids",
        }
        development_allowed = {
            "title", "description", "development_note", "development_due_date",
            "learning_session_reference", "evidence_attachment_ids",
            "message_follower_ids",
        }

        for line in self:
            if line.is_template:
                raise AccessError(_("Only Appraisal HR may edit template score lines."))
            if (
                line.form_id
                and line.form_id.state in ("consolidation", "closed", "cancelled")
                and line.line_type != "development"
            ):
                raise AccessError(
                    _("Performance evidence is frozen after the appraisal enters Consolidation.")
                )
            if line.rating_state == "submitted" and line.rater_type != "target":
                raise AccessError(_("Submitted ratings are locked; Appraisal HR must correct them."))

            is_manager = bool(
                is_appraisal_manager(self.env)
                and line.manager_user_id == self.env.user
            )
            is_employee = bool(line.employee_user_id == self.env.user)
            is_peer = bool(
                line.reviewer_user_id == self.env.user
            )

            if line.line_type == "development":
                if not (is_manager or is_employee):
                    raise AccessError(_("You are not authorized for this development action."))
                if set(vals) - development_allowed:
                    raise AccessError(_("Only development progress/evidence fields may be edited."))
            elif line.rater_type == "target":
                if not (is_manager or is_employee):
                    raise AccessError(_("You are not authorized to update this target evidence."))
                if set(vals) - target_allowed:
                    raise AccessError(_("Only target actual/evidence fields may be edited."))
            elif line.rater_type == "self":
                if not is_employee:
                    raise AccessError(_("Only the appraised employee may edit the Self rating."))
                if set(vals) - rating_allowed:
                    raise AccessError(_("Only rating/comment/evidence fields may be edited."))
            elif line.rater_type == "manager":
                if not is_manager:
                    raise AccessError(_("Only the assigned manager may edit the Manager rating."))
                if set(vals) - rating_allowed:
                    raise AccessError(_("Only rating/comment/evidence fields may be edited."))
            elif line.rater_type == "peer":
                if not is_peer:
                    raise AccessError(_("Only the assigned Peer Reviewer may edit this rating."))
                if set(vals) - rating_allowed:
                    raise AccessError(_("Only rating/comment/evidence fields may be edited."))
            else:
                raise AccessError(_("This score line is restricted to Appraisal HR."))

        return super().write(vals)

    @api.depends("target_value", "actual_value")
    def _compute_achievement(self):
        for line in self:
            line.achievement_percent = (
                line.actual_value * 100.0 / line.target_value
                if line.target_value else 0.0
            )

    @api.depends("rating", "weight", "cycle_id.rating_max")
    def _compute_normalized_score(self):
        for line in self:
            rating_max = line.cycle_id.rating_max or 0.0
            normalized = line.rating * 100.0 / rating_max if rating_max else 0.0
            line.normalized_score = normalized
            line.weighted_score = normalized * line.weight / 100.0

    @api.constrains("weight")
    def _check_weight(self):
        for line in self:
            if line.weight < 0 or line.weight > 100:
                raise ValidationError(_("Score line weight must be between 0 and 100."))

    @api.constrains("rating", "cycle_id")
    def _check_rating_range(self):
        for line in self:
            if not line.rating:
                continue
            if (
                line.rating < line.cycle_id.rating_min
                or line.rating > line.cycle_id.rating_max
            ):
                raise ValidationError(
                    _("Rating must be within the cycle scale: %s to %s.")
                    % (line.cycle_id.rating_min, line.cycle_id.rating_max)
                )

    @api.constrains("is_template", "form_id", "parent_score_id", "rater_type")
    def _check_structure(self):
        for line in self:
            if line.is_template:
                if line.form_id or line.parent_score_id:
                    raise ValidationError(
                        _("Template score lines cannot belong to an employee form.")
                    )
                if line.rater_type != "target":
                    raise ValidationError(
                        _("Template score lines must use Target / Template rater type.")
                    )
            elif not line.form_id:
                raise ValidationError(_("Operational score lines require an Appraisal Form."))
            if (
                line.parent_score_id
                and line.parent_score_id.form_id != line.form_id
            ):
                raise ValidationError(
                    _("Rating line and parent target must belong to the same Appraisal Form.")
                )

    @api.constrains(
        "cycle_id", "form_id", "parent_score_id", "is_template",
        "item_code", "line_type", "rater_type", "reviewer_employee_id",
    )
    def _check_duplicate_score_identity(self):
        for line in self:
            if line.line_type == "development":
                continue
            if line.rater_type == "target" and not (line.item_code or "").strip():
                raise ValidationError(
                    _("Objective/KPI target and template lines require an Item Code.")
                )
            domain = [
                ("id", "!=", line.id),
                ("cycle_id", "=", line.cycle_id.id),
                ("form_id", "=", line.form_id.id or False),
                ("parent_score_id", "=", line.parent_score_id.id or False),
                ("is_template", "=", line.is_template),
                ("item_code", "=", line.item_code or False),
                ("rater_type", "=", line.rater_type),
                ("reviewer_user_id", "=", line.reviewer_user_id.id or False),
            ]
            if self.search_count(domain, limit=1):
                raise ValidationError(
                    _("The same objective/rater/reviewer score identity already exists.")
                )

    @api.constrains("cycle_id", "form_id", "reviewer_employee_id")
    def _check_company_alignment(self):
        for line in self:
            if line.form_id and line.form_id.company_id != line.company_id:
                raise ValidationError(_("Score line and Appraisal Form company must match."))
            if (
                line.reviewer_company_id
                and line.reviewer_company_id != line.company_id
            ):
                raise ValidationError(_("Reviewer must belong to the appraisal company."))

    def action_open_parent_feedback(self):
        """Open all self/manager/peer feedback attached to this target row."""
        self.ensure_one()
        target = self.parent_score_id or self
        if target.rater_type != "target":
            raise UserError(_("Select a Target / Objective line first."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Multi-rater Feedback"),
            "res_model": "onehr.appraisal.score",
            "view_mode": "list,form",
            "domain": [("parent_score_id", "=", target.id)],
            "context": {
                "default_cycle_id": target.cycle_id.id,
                "default_form_id": target.form_id.id,
                "default_parent_score_id": target.id,
                "default_is_template": False,
            },
        }

    def action_submit_rating(self):
        for line in self:
            if line.rater_type not in ("self", "manager", "peer", "hr"):
                raise UserError(_("Only an actual rater line can be submitted."))
            if not line.rating:
                raise UserError(_("Enter a Rating before submitting."))

            if (
                line.rater_type == "self"
                and line.employee_user_id != self.env.user
                and not is_appraisal_hr(self.env)
            ):
                raise AccessError(_("This Self rating belongs to another employee."))
            if (
                line.rater_type == "manager"
                and line.manager_user_id != self.env.user
                and not is_appraisal_hr(self.env)
            ):
                raise AccessError(_("This Manager rating belongs to another manager."))
            if (
                line.rater_type == "peer"
                and line.reviewer_user_id != self.env.user
                and not is_appraisal_hr(self.env)
            ):
                raise AccessError(_("This Peer rating belongs to another reviewer."))

            line.with_context(onehr_appraisal_score_action=True).write(
                {"rating_state": "submitted"}
            )
            if line.form_id:
                line.form_id._refresh_peer_state()
        return display_notification(_("Rating submitted and locked."))

    def _require_development_line(self):
        self.ensure_one()
        if self.line_type != "development":
            raise UserError(_("This action is available only for Development lines."))

    def action_mark_development_planned(self):
        for line in self:
            line._require_development_line()
            line.with_context(onehr_appraisal_score_action=True).write(
                {"development_state": "planned"}
            )
        return display_notification(_("Development action marked Planned."))

    def action_start_development(self):
        for line in self:
            line._require_development_line()
            line.with_context(onehr_appraisal_score_action=True).write(
                {"development_state": "in_progress"}
            )
        return display_notification(_("Development action started."))

    def action_complete_development(self):
        for line in self:
            line._require_development_line()
            line.with_context(onehr_appraisal_score_action=True).write(
                {"development_state": "done"}
            )
        return display_notification(_("Development action completed."))

    def action_cancel_development(self):
        require_appraisal_hr(self)
        for line in self:
            line._require_development_line()
            line.with_context(onehr_appraisal_score_action=True).write(
                {"development_state": "cancelled"}
            )
        return display_notification(
            _("Development action cancelled."), notification_type="warning"
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_unstarted(self):
        for line in self:
            if line.is_template and line.cycle_id.state != "draft":
                raise UserError(
                    _("Appraisal target templates cannot be deleted after the Cycle leaves Draft.")
                )
            if line.rating_state == "submitted":
                raise UserError(_("Submitted appraisal rating evidence cannot be deleted."))
            if line.form_id and line.form_id.state != "draft":
                raise UserError(
                    _("Appraisal score/development evidence cannot be deleted after Review starts.")
                )

    def action_push_to_learning(self):
        require_appraisal_hr(self)
        self.ensure_one()
        self._require_development_line()
        if not self.learning_session_reference:
            raise UserError(_("Set an exact Learning Session Reference first."))
        if not self.env.registry.get("onehr.learning.enrollment"):
            raise UserError(
                _("OneHR Learning is not installed. The Appraisal record remains unchanged.")
            )
        if not self.form_id.employee_number:
            raise UserError(_("The employee requires a OneHR Employee Number."))

        payload = {
            "external_system": "ONEHR_APPRAISAL",
            "external_reference": f"APPRAISAL-SCORE-{self.id}",
            "employee_number": self.form_id.employee_number,
            "session_reference": self.learning_session_reference,
            "request_reason": self.title or _("Appraisal development action"),
            "submit_for_approval": True,
        }
        result = self.env["onehr.learning.enrollment"].onehr_external_enroll(payload)
        self.with_context(onehr_appraisal_score_action=True).write(
            {
                "learning_reference": (
                    f"Enrollment {result['enrollment_id']} / {result['state']}"
                )
            }
        )
        return display_notification(_("Development action handed off to OneHR Learning."))

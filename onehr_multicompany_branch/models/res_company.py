
# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .action_helpers import open_records_action


class ResCompany(models.Model):
    _inherit = "res.company"

    onehr_branch_enabled = fields.Boolean(
        string="Enable OneHR Branch Scope",
        default=True,
        help="Enables operational branch configuration. Company remains the legal/security partition.",
    )
    onehr_branch_ids = fields.One2many("onehr.branch", "company_id", string="OneHR Branches")
    onehr_default_branch_id = fields.Many2one(
        "onehr.branch",
        string="Default OneHR Branch",
        ondelete="restrict",
        help="Fallback branch used only when the user is explicitly allowed to use it.",
    )
    onehr_branch_count = fields.Integer(compute="_compute_onehr_branch_summary", string="Branches")
    onehr_effective_branch_count = fields.Integer(
        compute="_compute_onehr_branch_summary",
        string="Effective Branches",
    )

    @api.depends("onehr_branch_ids.active", "onehr_branch_ids.valid_from", "onehr_branch_ids.valid_to")
    def _compute_onehr_branch_summary(self):
        today = fields.Date.context_today(self)
        for company in self:
            company.onehr_branch_count = len(company.onehr_branch_ids)
            company.onehr_effective_branch_count = len(
                company.onehr_branch_ids.filtered(
                    lambda branch: branch.active and branch.is_effective_on(today)
                )
            )

    @api.constrains("onehr_default_branch_id", "onehr_branch_enabled")
    def _check_onehr_default_branch(self):
        today = fields.Date.context_today(self)
        for company in self:
            branch = company.onehr_default_branch_id
            if not branch:
                continue
            if branch.company_id != company:
                raise ValidationError(_("The default branch must belong to this legal company."))
            if not company.onehr_branch_enabled:
                raise ValidationError(_("Enable OneHR Branch Scope before selecting a default branch."))
            if not branch.active or not branch.is_effective_on(today):
                raise ValidationError(_("The company default branch must be active and effective today."))

    def action_open_onehr_branches(self):
        self.ensure_one()
        return open_records_action(
            name=_("Branches — %s", self.display_name),
            res_model="onehr.branch",
            domain=[("company_id", "=", self.id)],
            context={"default_company_id": self.id},
        )


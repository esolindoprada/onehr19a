# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError


class OneHRBranchMixin(models.AbstractModel):
    """Reusable branch ownership helpers for future branch-owned OneHR facts.

    The mixin deliberately does not make every OneHR record branch-specific.
    Source addons opt in only when branch is a genuine business dimension, as
    required by the OneHR Master Model Registry and Architecture v2.
    """

    _name = "onehr.mixin.branch"
    _description = "OneHR Branch Scope Mixin"

    branch_id = fields.Many2one(
        "onehr.branch",
        string="Branch",
        ondelete="restrict",
        index=True,
        check_company=True,
        default=lambda self: self._onehr_default_branch_id(),
    )

    @api.model
    def _onehr_default_branch(self, company=None, as_of_date=None):
        company = company or self.env.company
        as_of_date = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        user = self.env.user

        # A disabled company keeps historical branch data/rules intact, but no
        # new branch-owned business fact should default into that company.
        if not company.onehr_branch_enabled:
            return self.env["onehr.branch"]

        preferred = user.onehr_default_branch_id
        if (
            preferred
            and preferred.company_id == company
            and preferred in user.onehr_allowed_branch_ids
            and preferred.active
            and preferred.is_effective_on(as_of_date)
        ):
            return preferred

        company_default = company.onehr_default_branch_id
        if (
            company_default
            and company_default in user.onehr_allowed_branch_ids
            and company_default.active
            and company_default.is_effective_on(as_of_date)
        ):
            return company_default

        return user.onehr_allowed_branch_ids.filtered(
            lambda branch: (
                branch.company_id == company
                and branch.active
                and branch.is_effective_on(as_of_date)
            )
        )[:1]

    @api.model
    def _onehr_default_branch_id(self):
        return self._onehr_default_branch().id or False

    @api.model
    def _onehr_allowed_branch_domain(self, company=None, as_of_date=None, include_neutral=False):
        company = company or self.env.company
        as_of_date = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        branch_ids = []
        if company.onehr_branch_enabled:
            branch_ids = self.env.user.onehr_allowed_branch_ids.filtered(
                lambda branch: (
                    branch.company_id == company
                    and branch.active
                    and branch.is_effective_on(as_of_date)
                )
            ).ids
        domain = [("branch_id", "in", branch_ids)]
        if include_neutral:
            domain = ["|", ("branch_id", "=", False)] + domain
        return domain

    def _check_onehr_branch_access(self, branch=None, company=None, as_of_date=None):
        self.ensure_one()
        branch = branch or self.branch_id
        if not branch:
            return True

        company = company or (self.company_id if "company_id" in self._fields else self.env.company)
        as_of_date = fields.Date.to_date(as_of_date or fields.Date.context_today(self))
        if branch.company_id != company:
            raise ValidationError(_("Branch and legal company must match."))
        if not company.onehr_branch_enabled:
            raise ValidationError(_("OneHR Branch Scope is disabled for this legal company."))
        if branch not in self.env.user.onehr_allowed_branch_ids:
            raise AccessError(_("The selected branch is outside your explicit allowed-branch scope."))
        if not branch.active or not branch.is_effective_on(as_of_date):
            raise ValidationError(_("The selected branch is not active/effective for the requested date."))
        return True

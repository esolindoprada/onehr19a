
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .action_helpers import open_record_action
from .authority_helpers import require_assignment_officer


class OneHRAssignmentCostAllocation(models.Model):
    """Assignment-level costing split without owning accounting masters.

    Codes intentionally remain external-neutral. Payroll/accounting adapters can
    map them later without creating a hard dependency from Assignment to payroll,
    accounting or analytic modules.
    """

    _name = "onehr.assignment.cost.allocation"
    _description = "OneHR Assignment Cost Allocation"
    _inherit = ["onehr.mixin.audit"]
    _order = "assignment_id, valid_from, sequence, id"

    _INTERNAL_CONTEXT = "onehr_assignment_costing_controlled"

    assignment_id = fields.Many2one(
        "onehr.assignment", required=True, ondelete="cascade", index=True, tracking=True,
    )
    company_id = fields.Many2one(
        related="assignment_id.company_id", store=True, index=True, readonly=True,
    )
    sequence = fields.Integer(default=10)
    valid_from = fields.Date(required=True, index=True, tracking=True)
    valid_to = fields.Date(index=True, tracking=True)
    percentage = fields.Float(required=True, default=100.0, tracking=True)
    cost_center_code = fields.Char(index=True, tracking=True)
    project_code = fields.Char(index=True, tracking=True)
    product_line_code = fields.Char(index=True, tracking=True)
    external_dimension = fields.Char(
        tracking=True,
        help="Optional external costing dimension/key for payroll or finance adapters.",
    )
    note = fields.Char(tracking=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = self.browse()
        for incoming in vals_list:
            assignment = self.env["onehr.assignment"].browse(incoming.get("assignment_id")).exists()
            if not assignment:
                raise ValidationError(_("A valid Assignment is required."))
            require_assignment_officer(self)
            if assignment.state != "draft":
                raise AccessError(_("Cost allocation lines are editable only while the Assignment is Draft."))
            values = dict(incoming)
            values.setdefault("valid_from", assignment.effective_from)
            records |= super(OneHRAssignmentCostAllocation, self).create(values)
        records._validate_allocation_integrity()
        return records

    def write(self, values):
        if not self.env.context.get(self._INTERNAL_CONTEXT):
            require_assignment_officer(self)
            if any(line.assignment_id.state != "draft" for line in self):
                raise AccessError(_("Cost allocation lines are frozen after Assignment submission."))
        result = super().write(values)
        if not self.env.context.get(self._INTERNAL_CONTEXT):
            self._validate_allocation_integrity()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_draft_allocations_only(self):
        require_assignment_officer(self)
        if any(line.assignment_id.state != "draft" for line in self):
            raise AccessError(_("Cost allocation evidence cannot be deleted after Assignment submission."))

    @api.constrains(
        "assignment_id", "valid_from", "valid_to", "percentage",
        "cost_center_code", "project_code", "product_line_code", "external_dimension",
    )
    def _check_allocation_integrity(self):
        self._validate_allocation_integrity()

    def _validate_allocation_integrity(self):
        for line in self:
            assignment = line.assignment_id
            if line.percentage <= 0 or line.percentage > 100:
                raise ValidationError(_("Cost allocation percentage must be greater than 0 and not exceed 100."))
            if line.valid_to and line.valid_to < line.valid_from:
                raise ValidationError(_("Cost allocation End Date cannot be before Start Date."))
            if line.valid_from < assignment.effective_from:
                raise ValidationError(_("Cost allocation cannot start before the Assignment."))
            if assignment.effective_to and (not line.valid_to or line.valid_to > assignment.effective_to):
                raise ValidationError(_("Cost allocation validity must be contained by Assignment validity."))

            same_dimension = self.search([
                ("id", "!=", line.id),
                ("assignment_id", "=", assignment.id),
                ("cost_center_code", "=", line.cost_center_code or False),
                ("project_code", "=", line.project_code or False),
                ("product_line_code", "=", line.product_line_code or False),
                ("external_dimension", "=", line.external_dimension or False),
            ])
            for other in same_dimension:
                overlaps = (
                    (not line.valid_to or other.valid_from <= line.valid_to)
                    and (not other.valid_to or other.valid_to >= line.valid_from)
                )
                if overlaps:
                    raise ValidationError(
                        _("The same costing dimension cannot overlap within one Assignment.")
                    )
        return True

    def action_open_assignment(self):
        self.ensure_one()
        return open_record_action(
            name=self.assignment_id.display_name,
            res_model="onehr.assignment",
            res_id=self.assignment_id.id,
        )


class OneHRAssignmentCostingContract(models.Model):
    _inherit = "onehr.assignment"

    def _trim_cost_allocations_to_assignment_end(self, end_date):
        for assignment in self:
            lines = assignment.cost_allocation_ids.filtered(
                lambda line: not line.valid_to or line.valid_to > end_date
            )
            if lines:
                lines.with_context(onehr_assignment_costing_controlled=True).write({"valid_to": end_date})
        return True

    def _validate_cost_allocation_coverage(self):
        for assignment in self:
            lines = assignment.cost_allocation_ids
            if not assignment.costing_required:
                continue
            if not lines:
                raise ValidationError(_("Costing is required, but no allocation lines are defined."))

            boundaries = {assignment.effective_from}
            for line in lines:
                boundaries.add(line.valid_from)
                if line.valid_to:
                    next_day = line.valid_to + timedelta(days=1)
                    if not assignment.effective_to or next_day <= assignment.effective_to:
                        boundaries.add(next_day)

            for date_value in sorted(boundaries):
                if date_value < assignment.effective_from:
                    continue
                if assignment.effective_to and date_value > assignment.effective_to:
                    continue
                effective_lines = lines.filtered(
                    lambda line: line.valid_from <= date_value
                    and (not line.valid_to or line.valid_to >= date_value)
                )
                total = sum(effective_lines.mapped("percentage"))
                if abs(total - 100.0) > 0.0001:
                    raise ValidationError(
                        _(
                            "Cost allocations must total 100%% throughout the Assignment. "
                            "Total on %(date)s is %(total).2f%%.",
                            date=date_value,
                            total=total,
                        )
                    )
        return True

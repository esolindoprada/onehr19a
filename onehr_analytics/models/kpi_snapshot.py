from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


GROUP_MANAGER = "onehr_analytics.group_onehr_analytics_manager"
GROUP_ADMIN = "onehr_analytics.group_onehr_analytics_admin"


def _is_manager(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_MANAGER))


def _is_admin(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_ADMIN))


class OneHRKPISnapshot(models.Model):
    _name = "onehr.kpi.snapshot"
    _description = "OneHR KPI Snapshot"
    _inherit = ["onehr.mixin.analytics"]
    _order = "period_end desc, snapshot_at desc, id desc"
    _check_company_auto = True

    _unique_tile_period = models.Constraint(
        "UNIQUE(tile_id, period_start, period_end)",
        "A KPI tile can have only one immutable snapshot for the same period.",
    )

    name = fields.Char(compute="_compute_name", store=True, index=True)
    tile_id = fields.Many2one(
        "onehr.analytics.tile",
        required=True,
        ondelete="restrict",
        index=True,
        check_company=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="restrict",
        index=True,
    )
    branch_code = fields.Char(index=True)
    category = fields.Selection(related="tile_id.category", store=True, readonly=True, index=True)
    value_format = fields.Selection(related="tile_id.value_format", store=True, readonly=True)
    currency_id = fields.Many2one(related="tile_id.currency_id", store=True, readonly=True)

    snapshot_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    period_start = fields.Date(required=True, index=True)
    period_end = fields.Date(required=True, index=True)
    value = fields.Float(required=True)
    target_value = fields.Float()
    variance_value = fields.Float()
    status = fields.Selection(
        [
            ("normal", "Normal"),
            ("warning", "Warning"),
            ("critical", "Critical"),
            ("unavailable", "Unavailable"),
        ],
        required=True,
        default="normal",
        index=True,
    )

    source_name = fields.Char(required=True, index=True)
    source_record_count = fields.Integer()
    source_payload_json = fields.Text(
        groups="onehr_analytics.group_onehr_analytics_manager",
        help="Sanitized aggregate provider evidence only. Raw source records are never serialized here.",
    )
    drilldown_model_name = fields.Char(index=True)
    drilldown_domain_expression = fields.Text(default="[]")

    previous_value = fields.Float()
    previous_change_percent = fields.Float(string="Previous Period %")
    mom_baseline_value = fields.Float(string="MoM Baseline")
    mom_change_percent = fields.Float(string="MoM %")
    hoh_baseline_value = fields.Float(string="HoH Baseline")
    hoh_change_percent = fields.Float(string="HoH %")
    yoy_baseline_value = fields.Float(string="YoY Baseline")
    yoy_change_percent = fields.Float(string="YoY %")

    archived = fields.Boolean(default=False, index=True, copy=False)

    @api.depends("tile_id.code", "period_start", "period_end")
    def _compute_name(self):
        for snapshot in self:
            if snapshot.tile_id and snapshot.period_start and snapshot.period_end:
                snapshot.name = "%s · %s → %s" % (
                    snapshot.tile_id.code,
                    fields.Date.to_string(snapshot.period_start),
                    fields.Date.to_string(snapshot.period_end),
                )
            else:
                snapshot.name = _("New KPI Snapshot")

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for snapshot in self:
            if snapshot.period_start and snapshot.period_end and snapshot.period_end < snapshot.period_start:
                raise ValidationError(_("KPI snapshot Date To cannot be before Date From."))

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("onehr_analytics_snapshot_create"):
            raise AccessError(_("KPI snapshots are technical evidence. Create them through an active KPI tile."))
        for vals in vals_list:
            tile = self.env["onehr.analytics.tile"].browse(vals.get("tile_id")).exists()
            if not tile:
                raise ValidationError(_("KPI snapshot requires a valid KPI tile."))
            if vals.get("company_id") != tile.company_id.id:
                raise ValidationError(_("KPI snapshot company must match the KPI tile company."))
        return super().create(vals_list)

    def write(self, vals):
        if set(vals) != {"archived"} or not self.env.context.get("onehr_analytics_archive"):
            raise AccessError(_("KPI snapshot evidence is immutable. Only controlled archive/restore is allowed."))
        if not _is_manager(self.env):
            raise AccessError(_("Archiving KPI evidence requires OneHR Analytics Manager authority."))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("KPI snapshot evidence cannot be deleted through the application."))

    def action_open_snapshot(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "onehr.kpi.snapshot",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_tile(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.tile_id.display_name,
            "res_model": "onehr.analytics.tile",
            "res_id": self.tile_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_source(self):
        self.ensure_one()
        if not self.drilldown_model_name:
            raise UserError(_("This snapshot has no source-record drill-through."))
        if not self.env.registry.get(self.drilldown_model_name):
            raise UserError(_("The source model is no longer installed: %s") % self.drilldown_model_name)
        Model = self.env[self.drilldown_model_name]
        Model.check_access("read")
        domain = self._analytics_parse_domain(self.drilldown_domain_expression)
        return {
            "type": "ir.actions.act_window",
            "name": _("Snapshot Source — %s") % self.tile_id.name,
            "res_model": self.drilldown_model_name,
            "view_mode": "list,form",
            "domain": domain,
        }

    def action_archive_evidence(self):
        if not _is_manager(self.env):
            raise AccessError(_("Archiving KPI evidence requires OneHR Analytics Manager authority."))
        self.with_context(onehr_analytics_archive=True).write({"archived": True})
        return True

    def action_restore_evidence(self):
        if not _is_admin(self.env):
            raise AccessError(_("Restoring archived KPI evidence requires OneHR Analytics Administrator authority."))
        self.with_context(onehr_analytics_archive=True).write({"archived": False})
        return True

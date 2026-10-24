import base64
import csv
import io
import re
from datetime import timedelta

from odoo import Command, _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .provider_engine import (
    AnalyticsProviderEngine,
    SERVICE_METRIC_SELECTION,
    SOURCE_MODEL_SELECTION,
)


GROUP_ANALYST = "onehr_analytics.group_onehr_analytics_analyst"
GROUP_MANAGER = "onehr_analytics.group_onehr_analytics_manager"
GROUP_ADMIN = "onehr_analytics.group_onehr_analytics_admin"


def _is_manager(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_MANAGER))


def _is_admin(env):
    return bool(env.is_superuser() or env.user.has_group(GROUP_ADMIN))


def _require_manager(recordset):
    if not _is_manager(recordset.env):
        raise AccessError(_("This action requires OneHR Analytics Manager authority."))


class OneHRAnalyticsTile(models.Model):
    _name = "onehr.analytics.tile"
    _description = "OneHR Analytics KPI Tile"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.analytics"]
    _order = "sequence, category, name, id"
    _check_company_auto = True

    _unique_code_company = models.Constraint(
        "UNIQUE(company_id, code)",
        "KPI tile code must be unique inside a company.",
    )

    name = fields.Char(required=True, tracking=True, index=True)
    code = fields.Char(required=True, tracking=True, index=True)
    description = fields.Text()
    sequence = fields.Integer(default=10, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        ondelete="cascade",
        index=True,
        tracking=True,
    )
    branch_code = fields.Char(
        index=True,
        tracking=True,
        help="Optional soft branch reference. If set, the provider fails closed unless the source model exposes branch_id and onehr.branch resolves exactly once.",
    )
    category = fields.Selection(
        [
            ("workforce", "Workforce"),
            ("recruitment", "Recruitment"),
            ("attendance", "Attendance & Time Off"),
            ("learning", "Learning & Development"),
            ("payroll", "Payroll & Compensation"),
            ("performance", "Performance & Succession"),
            ("compliance", "Compliance & Discipline"),
            ("custom", "Custom / Executive"),
        ],
        required=True,
        default="workforce",
        index=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("paused", "Paused"),
            ("retired", "Retired"),
        ],
        required=True,
        default="draft",
        tracking=True,
        index=True,
    )

    # Provider definition -------------------------------------------------
    provider_mode = fields.Selection(
        [
            ("manual", "Manual Value"),
            ("model_aggregate", "Approved Model Aggregate"),
            ("service", "OneHR KPI Service Contract"),
        ],
        required=True,
        default="manual",
        tracking=True,
    )
    manual_value = fields.Float(tracking=True)
    source_model_name = fields.Selection(SOURCE_MODEL_SELECTION, tracking=True)
    aggregate_function = fields.Selection(
        [("count", "Count"), ("sum", "Sum"), ("average", "Average")],
        default="count",
        required=True,
        tracking=True,
    )
    measure_field_name = fields.Char(tracking=True)
    date_field_name = fields.Char(
        tracking=True,
        help="Optional Date/Datetime field used to restrict model aggregates to each snapshot period.",
    )
    domain_expression = fields.Text(
        default="[]",
        help="Literal Odoo domain only. Python expressions, eval and safe_eval are intentionally unsupported.",
    )
    service_metric_key = fields.Selection(SERVICE_METRIC_SELECTION, tracking=True)

    # Presentation and target --------------------------------------------
    value_format = fields.Selection(
        [
            ("number", "Number"),
            ("percent", "Percent"),
            ("hours", "Hours"),
            ("days", "Days"),
            ("currency", "Currency"),
        ],
        required=True,
        default="number",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    target_value = fields.Float(tracking=True)
    threshold_direction = fields.Selection(
        [
            ("none", "No Threshold"),
            ("high_bad", "Higher Is Worse"),
            ("low_bad", "Lower Is Worse"),
        ],
        required=True,
        default="none",
        tracking=True,
    )
    warning_threshold = fields.Float(tracking=True)
    critical_threshold = fields.Float(tracking=True)

    # Scheduling and retention -------------------------------------------
    snapshot_frequency = fields.Selection(
        [
            ("manual", "Manual"),
            ("daily", "Daily"),
            ("weekly", "Weekly"),
            ("monthly", "Monthly"),
        ],
        required=True,
        default="monthly",
        tracking=True,
        index=True,
    )
    next_snapshot_date = fields.Date(index=True, tracking=True)
    retention_months = fields.Integer(
        default=84,
        tracking=True,
        help="Old snapshots are archived, never deleted, after this many months. Set 0 to disable automatic archival.",
    )

    # Alerts / ownership / favorite --------------------------------------
    owner_user_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        tracking=True,
        index=True,
    )
    alert_user_ids = fields.Many2many(
        "res.users",
        "onehr_analytics_tile_alert_user_rel",
        "tile_id",
        "user_id",
        string="Alert Recipients",
    )
    favorite_user_ids = fields.Many2many(
        "res.users",
        "onehr_analytics_tile_favorite_user_rel",
        "tile_id",
        "user_id",
        string="Favorite Users",
        copy=False,
    )
    is_favorite = fields.Boolean(compute="_compute_is_favorite")

    # Cached executive values --------------------------------------------
    last_snapshot_at = fields.Datetime(readonly=True, copy=False, index=True)
    last_value = fields.Float(readonly=True, copy=False)
    last_status = fields.Selection(
        [
            ("normal", "Normal"),
            ("warning", "Warning"),
            ("critical", "Critical"),
            ("unavailable", "Unavailable"),
        ],
        readonly=True,
        copy=False,
        default="normal",
        index=True,
    )
    last_error_message = fields.Char(readonly=True, copy=False)

    snapshot_ids = fields.One2many("onehr.kpi.snapshot", "tile_id", string="KPI Snapshots", readonly=True)
    snapshot_count = fields.Integer(compute="_compute_snapshot_counts")
    breached_snapshot_count = fields.Integer(compute="_compute_snapshot_counts")

    export_file = fields.Binary(readonly=True, copy=False, attachment=False)
    export_filename = fields.Char(readonly=True, copy=False)

    @api.depends("favorite_user_ids")
    def _compute_is_favorite(self):
        current_user = self.env.user
        for tile in self:
            tile.is_favorite = current_user in tile.favorite_user_ids

    @api.depends("snapshot_ids", "snapshot_ids.status")
    def _compute_snapshot_counts(self):
        for tile in self:
            tile.snapshot_count = len(tile.snapshot_ids)
            tile.breached_snapshot_count = len(
                tile.snapshot_ids.filtered(lambda item: item.status in ("warning", "critical"))
            )

    @api.constrains("code")
    def _check_code(self):
        pattern = re.compile(r"^[a-z][a-z0-9_.-]{2,63}$")
        for tile in self:
            if tile.code and not pattern.fullmatch(tile.code):
                raise ValidationError(
                    _("KPI code must start with a lowercase letter and contain only lowercase letters, digits, dot, underscore or hyphen (3-64 chars).")
                )

    @api.constrains("warning_threshold", "critical_threshold", "threshold_direction")
    def _check_threshold_order(self):
        for tile in self:
            if tile.threshold_direction == "high_bad" and tile.warning_threshold and tile.critical_threshold:
                if tile.critical_threshold < tile.warning_threshold:
                    raise ValidationError(_("For Higher Is Worse, Critical threshold cannot be below Warning threshold."))
            if tile.threshold_direction == "low_bad" and tile.warning_threshold and tile.critical_threshold:
                if tile.critical_threshold > tile.warning_threshold:
                    raise ValidationError(_("For Lower Is Worse, Critical threshold cannot be above Warning threshold."))

    @api.constrains("retention_months")
    def _check_retention(self):
        for tile in self:
            if tile.retention_months < 0 or tile.retention_months > 240:
                raise ValidationError(_("Snapshot retention must be between 0 and 240 months."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("code"):
                vals["code"] = vals["code"].strip().lower()
            if vals.get("branch_code"):
                vals["branch_code"] = vals["branch_code"].strip().upper()
            if vals.get("state") not in (None, "draft") and not self.env.context.get("onehr_analytics_lifecycle"):
                raise AccessError(_("Create KPI tiles in Draft and use lifecycle actions."))
        return super().create(vals_list)

    def write(self, vals):
        if not _is_manager(self.env):
            if set(vals) != {"favorite_user_ids"}:
                raise AccessError(_("Analytics Analysts may only change their own KPI favorite flag."))
            self._validate_analyst_favorite_commands(vals["favorite_user_ids"])

        if "state" in vals and not self.env.context.get("onehr_analytics_lifecycle"):
            raise AccessError(_("Use the KPI lifecycle action buttons to change status."))

        identity_fields = {
            "company_id",
            "branch_code",
            "provider_mode",
            "source_model_name",
            "aggregate_function",
            "measure_field_name",
            "date_field_name",
            "domain_expression",
            "service_metric_key",
        }
        if identity_fields.intersection(vals):
            if any(tile.state == "active" for tile in self):
                raise AccessError(_("Pause an active KPI before changing its source/provider identity."))
            if any(tile.state == "retired" for tile in self):
                raise AccessError(_("A retired KPI definition is immutable."))

        if vals.get("code"):
            vals["code"] = vals["code"].strip().lower()
        if vals.get("branch_code"):
            vals["branch_code"] = vals["branch_code"].strip().upper()
        return super().write(vals)

    def _validate_analyst_favorite_commands(self, commands):
        current_id = self.env.user.id
        for tile in self:
            before = set(tile.favorite_user_ids.ids)
            after = set(before)
            for command in commands:
                operation = command[0]
                if operation == Command.LINK:
                    if command[1] != current_id:
                        raise AccessError(_("Analysts may favorite a KPI only for themselves."))
                    after.add(command[1])
                elif operation == Command.UNLINK:
                    if command[1] != current_id:
                        raise AccessError(_("Analysts may remove only their own KPI favorite."))
                    after.discard(command[1])
                elif operation == Command.SET:
                    after = set(command[2])
                elif operation == Command.CLEAR:
                    after = set()
                else:
                    raise AccessError(_("Unsupported favorite operation for Analytics Analyst."))
            if before.symmetric_difference(after) - {current_id}:
                raise AccessError(_("Analysts cannot alter another user's KPI favorite."))
        return True

    def unlink(self):
        if not _is_admin(self.env):
            raise AccessError(_("Only an Analytics Administrator may delete an unused draft KPI."))
        for tile in self:
            if tile.state != "draft" or tile.snapshot_ids:
                raise AccessError(_("Started KPI definitions are retained. Retire them instead of deleting them."))
        return super().unlink()

    # Lifecycle -----------------------------------------------------------
    def action_activate(self):
        _require_manager(self)
        for tile in self:
            if tile.state not in ("draft", "paused"):
                raise UserError(_("Only Draft or Paused KPI tiles can be activated."))
            tile._validate_provider_configuration()
            next_date = fields.Date.context_today(tile)
            tile.with_context(onehr_analytics_lifecycle=True).write({
                "state": "active",
                "next_snapshot_date": next_date if tile.snapshot_frequency != "manual" else False,
                "last_error_message": False,
            })
        return True

    def action_pause(self):
        _require_manager(self)
        for tile in self:
            if tile.state != "active":
                raise UserError(_("Only an Active KPI tile can be paused."))
            tile.with_context(onehr_analytics_lifecycle=True).write({"state": "paused"})
        return True

    def action_resume(self):
        return self.action_activate()

    def action_retire(self):
        _require_manager(self)
        for tile in self:
            if tile.state == "retired":
                continue
            tile.with_context(onehr_analytics_lifecycle=True).write({
                "state": "retired",
                "next_snapshot_date": False,
            })
        return True

    # Provider / snapshot operations -------------------------------------
    def _validate_provider_configuration(self):
        self.ensure_one()
        if self.company_id not in self.env.companies:
            raise AccessError(_("The KPI company is outside the current user's allowed companies."))
        period_start, period_end = self._analytics_period_bounds(self.snapshot_frequency)
        return AnalyticsProviderEngine(self, period_start, period_end).validate_configuration()

    def action_test_provider(self):
        _require_manager(self)
        self.ensure_one()
        period_start, period_end = self._analytics_period_bounds(self.snapshot_frequency)
        result = AnalyticsProviderEngine(self, period_start, period_end).evaluate()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("KPI Provider Test"),
                "message": _("Provider returned %(value)s from %(source)s for %(date_from)s to %(date_to)s.") % {
                    "value": result["value"],
                    "source": result["source"],
                    "date_from": period_start,
                    "date_to": period_end,
                },
                "type": "success",
                "sticky": False,
            },
        }

    def action_snapshot_now(self):
        _require_manager(self)
        self.ensure_one()
        if self.state != "active":
            raise UserError(_("Activate the KPI before generating snapshot evidence."))
        period_start, period_end = self._analytics_period_bounds(self.snapshot_frequency)
        snapshot = self._generate_snapshot(period_start, period_end)
        return snapshot.action_open_snapshot()

    def _generate_snapshot(self, period_start, period_end):
        self.ensure_one()
        Snapshot = self.env["onehr.kpi.snapshot"]
        existing = Snapshot.search([
            ("tile_id", "=", self.id),
            ("period_start", "=", period_start),
            ("period_end", "=", period_end),
        ], limit=1)
        if existing:
            return existing

        result = AnalyticsProviderEngine(self, period_start, period_end).evaluate()
        value = float(result["value"] or 0.0)
        status = self._analytics_threshold_status(
            value,
            self.threshold_direction,
            self.warning_threshold,
            self.critical_threshold,
        )

        values = self._prepare_snapshot_values(period_start, period_end, result, status)
        snapshot = Snapshot.with_context(onehr_analytics_snapshot_create=True).create(values)
        self.write({
            "last_snapshot_at": snapshot.snapshot_at,
            "last_value": snapshot.value,
            "last_status": snapshot.status,
            "last_error_message": False,
            "next_snapshot_date": self._analytics_next_snapshot_date(
                self.snapshot_frequency,
                fields.Date.context_today(self),
            ),
        })
        self._schedule_threshold_activities(snapshot)
        return snapshot

    def _prepare_snapshot_values(self, period_start, period_end, result, status):
        self.ensure_one()
        Snapshot = self.env["onehr.kpi.snapshot"]
        previous = Snapshot.search([
            ("tile_id", "=", self.id),
            ("period_start", "<", period_start),
        ], order="period_start desc, id desc", limit=1)

        month_date = self._analytics_shift_date(period_start, months=-1)
        half_date = self._analytics_shift_date(period_start, months=-6)
        year_date = self._analytics_shift_date(period_start, years=-1)
        mom = self._baseline_snapshot_value(month_date)
        hoh = self._baseline_snapshot_value(half_date)
        yoy = self._baseline_snapshot_value(year_date)

        value = float(result["value"] or 0.0)
        target = float(self.target_value or 0.0)
        return {
            "tile_id": self.id,
            "company_id": self.company_id.id,
            "branch_code": self.branch_code or False,
            "snapshot_at": fields.Datetime.now(),
            "period_start": period_start,
            "period_end": period_end,
            "value": value,
            "target_value": target,
            "variance_value": value - target,
            "status": status,
            "source_name": result["source"],
            "source_record_count": result["record_count"],
            "source_payload_json": self._analytics_json(result["payload"]),
            "drilldown_model_name": result["drilldown_model"] or False,
            "drilldown_domain_expression": repr(result["drilldown_domain"] or []),
            "previous_value": previous.value if previous else 0.0,
            "previous_change_percent": self._analytics_percent_change(value, previous.value) if previous else 0.0,
            "mom_baseline_value": mom,
            "mom_change_percent": self._analytics_percent_change(value, mom),
            "hoh_baseline_value": hoh,
            "hoh_change_percent": self._analytics_percent_change(value, hoh),
            "yoy_baseline_value": yoy,
            "yoy_change_percent": self._analytics_percent_change(value, yoy),
        }

    def _baseline_snapshot_value(self, target_date):
        self.ensure_one()
        snapshot = self.env["onehr.kpi.snapshot"].search([
            ("tile_id", "=", self.id),
            ("period_start", "<=", target_date),
        ], order="period_start desc, id desc", limit=1)
        return float(snapshot.value or 0.0) if snapshot else 0.0

    def _schedule_threshold_activities(self, snapshot):
        self.ensure_one()
        if snapshot.status not in ("warning", "critical"):
            return True
        recipients = self.alert_user_ids or self.owner_user_id
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        summary = _("Analytics %(status)s — %(code)s — %(period)s") % {
            "status": snapshot.status.title(),
            "code": self.code,
            "period": fields.Date.to_string(snapshot.period_end),
        }
        for recipient in recipients:
            duplicate = self.activity_ids.filtered(
                lambda item, user=recipient: item.user_id == user and item.summary == summary
            )
            if duplicate:
                continue
            self.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=recipient.id,
                summary=summary,
                note=_("KPI %(name)s recorded %(value)s with %(status)s threshold status.") % {
                    "name": self.name,
                    "value": snapshot.value,
                    "status": snapshot.status,
                },
                date_deadline=fields.Date.context_today(self) + timedelta(days=1),
            )
        return True

    # Navigation / export -------------------------------------------------
    def action_open_snapshots(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("KPI Snapshots — %s") % self.name,
            "res_model": "onehr.kpi.snapshot",
            "view_mode": "list,graph,pivot,form",
            "domain": [("tile_id", "=", self.id)],
            "context": {"default_tile_id": self.id},
        }

    def action_open_breaches(self):
        self.ensure_one()
        action = self.action_open_snapshots()
        action["name"] = _("Threshold Breaches — %s") % self.name
        action["domain"] = [("tile_id", "=", self.id), ("status", "in", ("warning", "critical"))]
        return action

    def action_open_source_records(self):
        self.ensure_one()
        period_start, period_end = self._analytics_period_bounds(self.snapshot_frequency)
        result = AnalyticsProviderEngine(self, period_start, period_end).evaluate()
        if not result["drilldown_model"]:
            raise UserError(_("This KPI provider has no source-record drill-through."))
        Model = self.env[result["drilldown_model"]]
        Model.check_access("read")
        return {
            "type": "ir.actions.act_window",
            "name": _("Source Records — %s") % self.name,
            "res_model": result["drilldown_model"],
            "view_mode": "list,form",
            "domain": result["drilldown_domain"],
        }

    def action_toggle_favorite(self):
        self.ensure_one()
        if self.env.user in self.favorite_user_ids:
            self.write({"favorite_user_ids": [Command.unlink(self.env.user.id)]})
        else:
            self.write({"favorite_user_ids": [Command.link(self.env.user.id)]})
        return True

    def action_export_snapshot_csv(self):
        self.ensure_one()
        _require_manager(self)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "kpi_code", "kpi_name", "company", "branch", "snapshot_at",
            "period_start", "period_end", "value", "target", "variance", "status",
            "previous_change_percent", "mom_change_percent", "hoh_change_percent",
            "yoy_change_percent", "source", "source_record_count",
        ])
        for snapshot in self.snapshot_ids.sorted(lambda item: (item.period_start, item.id)):
            writer.writerow([
                self.code,
                self.name,
                self.company_id.display_name,
                snapshot.branch_code or "",
                fields.Datetime.to_string(snapshot.snapshot_at),
                fields.Date.to_string(snapshot.period_start),
                fields.Date.to_string(snapshot.period_end),
                snapshot.value,
                snapshot.target_value,
                snapshot.variance_value,
                snapshot.status,
                snapshot.previous_change_percent,
                snapshot.mom_change_percent,
                snapshot.hoh_change_percent,
                snapshot.yoy_change_percent,
                snapshot.source_name,
                snapshot.source_record_count,
            ])
        content = output.getvalue().encode("utf-8-sig")
        filename = f"onehr_analytics_{self.code}_snapshots.csv"
        self.write({"export_file": base64.b64encode(content), "export_filename": filename})
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/onehr.analytics.tile/{self.id}/export_file/{filename}?download=true",
            "target": "self",
        }

    # Downstream model-service boundary ----------------------------------
    @api.model
    def onehr_analytics_kpi_feed(self, company=None, category=None):
        company = company or self.env.company
        domain = [("company_id", "=", company.id), ("state", "=", "active")]
        if category:
            domain.append(("category", "=", category))
        tiles = self.search(domain, order="sequence, category, name")
        return [
            {
                "tile_id": tile.id,
                "code": tile.code,
                "name": tile.name,
                "category": tile.category,
                "company_id": tile.company_id.id,
                "branch_code": tile.branch_code or False,
                "value": tile.last_value,
                "value_format": tile.value_format,
                "target_value": tile.target_value,
                "status": tile.last_status,
                "last_snapshot_at": fields.Datetime.to_string(tile.last_snapshot_at) if tile.last_snapshot_at else False,
            }
            for tile in tiles
        ]

    # Scheduler -----------------------------------------------------------
    @api.model
    def _cron_generate_due_snapshots(self):
        today = fields.Date.context_today(self)
        tiles = self.search([
            ("state", "=", "active"),
            ("snapshot_frequency", "!=", "manual"),
            "|",
            ("next_snapshot_date", "=", False),
            ("next_snapshot_date", "<=", today),
        ], order="company_id, sequence, id", limit=250)
        for tile in tiles:
            try:
                period_start, period_end = tile._analytics_period_bounds(tile.snapshot_frequency, today)
                tile._generate_snapshot(period_start, period_end)
            except Exception as exc:
                # A single optional-provider failure must not block unrelated KPI tiles.
                # The error is surfaced on the tile and remains visible to managers.
                tile.write({
                    "last_status": "unavailable",
                    "last_error_message": str(exc)[:512],
                    "next_snapshot_date": tile._analytics_next_snapshot_date(tile.snapshot_frequency, today),
                })
        return True

    @api.model
    def _cron_archive_old_snapshots(self):
        today = fields.Date.context_today(self)
        tiles = self.search([("retention_months", ">", 0)], order="company_id, id", limit=500)
        Snapshot = self.env["onehr.kpi.snapshot"]
        for tile in tiles:
            cutoff = self._analytics_shift_date(today, months=-tile.retention_months)
            old = Snapshot.search([
                ("tile_id", "=", tile.id),
                ("period_end", "<", cutoff),
                ("archived", "=", False),
            ], limit=1000)
            if old:
                old.with_context(onehr_analytics_archive=True).write({"archived": True})
        return True

from datetime import datetime, time, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import require_recruitment_manager


class OneHRRecruitmentSourceMetric(models.Model):
    """Immutable ED4 source/funnel snapshot for period-based reporting."""

    _name = "onehr.recruitment.source.metric"
    _description = "OneHR Recruitment Source Metric"
    _inherit = ["onehr.mixin.audit"]
    _order = "period_end desc, company_id, job_id, source_id"

    name = fields.Char(compute="_compute_name", store=True, index=True)
    company_id = fields.Many2one(
        "res.company", required=True, index=True, ondelete="restrict"
    )
    period_start = fields.Date(required=True, index=True)
    period_end = fields.Date(required=True, index=True)
    job_id = fields.Many2one(
        "hr.job", index=True, ondelete="restrict", check_company=True
    )
    source_id = fields.Many2one(
        "utm.source", string="Recruitment Source", index=True, ondelete="set null"
    )
    application_count = fields.Integer(readonly=True)
    interviewed_count = fields.Integer(readonly=True)
    offered_count = fields.Integer(readonly=True)
    accepted_offer_count = fields.Integer(readonly=True)
    hired_count = fields.Integer(readonly=True)
    offer_acceptance_rate = fields.Float(readonly=True, digits=(16, 2))
    hire_conversion_rate = fields.Float(readonly=True, digits=(16, 2))
    average_time_to_hire_days = fields.Float(readonly=True, digits=(16, 2))

    @api.depends("company_id.name", "period_start", "period_end", "job_id.name", "source_id.name")
    def _compute_name(self):
        for metric in self:
            scope = metric.job_id.name or _("All Jobs")
            source = metric.source_id.name or _("No Source")
            metric.name = _("%s / %s / %s — %s", scope, source, metric.period_start or "", metric.period_end or "")

    @api.model_create_multi
    def create(self, vals_list):
        require_recruitment_manager(self)
        records = super().create(vals_list)
        records._check_unique_snapshot()
        return records

    def write(self, values):
        raise AccessError(_("Recruitment source metrics are immutable snapshots. Generate a new period instead."))

    def _check_unique_snapshot(self):
        for metric in self:
            if self.search_count([
                ("id", "!=", metric.id),
                ("company_id", "=", metric.company_id.id),
                ("period_start", "=", metric.period_start),
                ("period_end", "=", metric.period_end),
                ("job_id", "=", metric.job_id.id or False),
                ("source_id", "=", metric.source_id.id or False),
            ]):
                raise ValidationError(_("A recruitment source snapshot already exists for this period and scope."))

    @api.constrains("period_start", "period_end")
    def _check_period(self):
        for metric in self:
            if metric.period_end < metric.period_start:
                raise ValidationError(_("Metric period end cannot be before period start."))

    @api.constrains(
        "application_count", "interviewed_count", "offered_count", "accepted_offer_count", "hired_count"
    )
    def _check_funnel_counts(self):
        for metric in self:
            values = [
                metric.application_count,
                metric.interviewed_count,
                metric.offered_count,
                metric.accepted_offer_count,
                metric.hired_count,
            ]
            if min(values) < 0:
                raise ValidationError(_("Recruitment funnel counts cannot be negative."))
            if any(value > metric.application_count for value in values[1:]):
                raise ValidationError(_("Interview/offer/hire counts cannot exceed applications in the snapshot."))

    @api.model
    def build_snapshot(self, *, period_start, period_end, company, job=None):
        """Idempotently build source snapshots without rewriting older ED4 evidence."""
        require_recruitment_manager(self)
        period_start = fields.Date.to_date(period_start)
        period_end = fields.Date.to_date(period_end)
        if period_end < period_start:
            raise UserError(_("Snapshot period end cannot be before period start."))

        start_dt = datetime.combine(period_start, time.min)
        end_dt = datetime.combine(period_end + timedelta(days=1), time.min)
        applicant_domain = [
            ("company_id", "=", company.id),
            ("create_date", ">=", fields.Datetime.to_string(start_dt)),
            ("create_date", "<", fields.Datetime.to_string(end_dt)),
        ]
        if job:
            applicant_domain.append(("job_id", "=", job.id))
        applicants = self.env["hr.applicant"].search(applicant_domain)
        source_keys = {app.source_id.id if app.source_id else False for app in applicants} or {False}
        result = self.browse()

        for source_id in sorted(source_keys, key=lambda value: value or 0):
            bucket = applicants.filtered(lambda app: (app.source_id.id if app.source_id else False) == source_id)
            existing = self.search([
                ("company_id", "=", company.id),
                ("period_start", "=", period_start),
                ("period_end", "=", period_end),
                ("job_id", "=", job.id if job else False),
                ("source_id", "=", source_id),
            ], limit=1)
            if existing:
                result |= existing
                continue

            applicant_ids = bucket.ids
            completed_sessions = self.env["onehr.interview.session"].search([
                ("applicant_id", "in", applicant_ids), ("state", "=", "completed")
            ]) if applicant_ids else self.env["onehr.interview.session"].browse()
            offers = self.env["onehr.offer"].search([
                ("applicant_id", "in", applicant_ids),
                ("state", "in", ["approved", "sent", "accepted", "declined", "withdrawn", "expired"]),
            ]) if applicant_ids else self.env["onehr.offer"].browse()
            accepted_offers = offers.filtered(lambda offer: offer.state == "accepted")
            hired = bucket.filtered(lambda app: app.application_status == "hired")

            interviewed_count = len(set(completed_sessions.mapped("applicant_id").ids))
            offered_count = len(set(offers.mapped("applicant_id").ids))
            accepted_count = len(set(accepted_offers.mapped("applicant_id").ids))
            hired_count = len(hired)
            time_to_hire = []
            for applicant in hired:
                if applicant.create_date and applicant.date_closed:
                    created = fields.Datetime.to_datetime(applicant.create_date).date()
                    closed = fields.Date.to_date(applicant.date_closed)
                    time_to_hire.append(max((closed - created).days, 0))

            application_count = len(bucket)
            metric = self.create({
                "company_id": company.id,
                "period_start": period_start,
                "period_end": period_end,
                "job_id": job.id if job else False,
                "source_id": source_id,
                "application_count": application_count,
                "interviewed_count": interviewed_count,
                "offered_count": offered_count,
                "accepted_offer_count": accepted_count,
                "hired_count": hired_count,
                "offer_acceptance_rate": (accepted_count / offered_count * 100.0) if offered_count else 0.0,
                "hire_conversion_rate": (hired_count / application_count * 100.0) if application_count else 0.0,
                "average_time_to_hire_days": sum(time_to_hire) / len(time_to_hire) if time_to_hire else 0.0,
            })
            result |= metric
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise UserError(_("Recruitment source metrics are retained as immutable period snapshots."))

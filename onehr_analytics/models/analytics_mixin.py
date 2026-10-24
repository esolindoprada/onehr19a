import ast
import json
from datetime import date, datetime, time, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class OneHRAnalyticsMixin(models.AbstractModel):
    """Reusable analytics helpers with no business-domain ownership.

    This mixin deliberately works with aggregate values and date boundaries only.
    It never elevates privileges and never exposes source records by itself.
    """

    _name = "onehr.mixin.analytics"
    _description = "OneHR Analytics Utility Mixin"

    def _analytics_period_bounds(self, frequency, anchor_date=None):
        anchor = fields.Date.to_date(anchor_date or fields.Date.context_today(self))
        if frequency in (False, "manual", "daily"):
            return anchor, anchor
        if frequency == "weekly":
            start = anchor - timedelta(days=anchor.weekday())
            return start, start + timedelta(days=6)
        if frequency == "monthly":
            start = anchor.replace(day=1)
            return start, start + relativedelta(months=1, days=-1)
        raise ValidationError(_("Unsupported analytics snapshot frequency: %s") % frequency)

    def _analytics_next_snapshot_date(self, frequency, anchor_date=None):
        anchor = fields.Date.to_date(anchor_date or fields.Date.context_today(self))
        if frequency in (False, "manual"):
            return False
        if frequency == "daily":
            return anchor + timedelta(days=1)
        if frequency == "weekly":
            return anchor + timedelta(days=(7 - anchor.weekday()))
        if frequency == "monthly":
            return anchor.replace(day=1) + relativedelta(months=1)
        raise ValidationError(_("Unsupported analytics snapshot frequency: %s") % frequency)

    def _analytics_percent_change(self, current, baseline):
        current = float(current or 0.0)
        baseline = float(baseline or 0.0)
        if not baseline:
            return 0.0
        return ((current - baseline) / abs(baseline)) * 100.0

    def _analytics_threshold_status(self, value, direction, warning, critical):
        value = float(value or 0.0)
        if direction == "none":
            return "normal"

        warning = float(warning or 0.0)
        critical = float(critical or 0.0)
        if direction == "high_bad":
            if critical and value >= critical:
                return "critical"
            if warning and value >= warning:
                return "warning"
            return "normal"

        if direction == "low_bad":
            if critical and value <= critical:
                return "critical"
            if warning and value <= warning:
                return "warning"
            return "normal"

        raise ValidationError(_("Unsupported threshold direction: %s") % direction)

    def _analytics_parse_domain(self, domain_expression):
        """Parse a literal Odoo domain; never execute Python/eval/safe_eval."""
        if not domain_expression or not domain_expression.strip():
            return []
        try:
            domain = ast.literal_eval(domain_expression.strip())
        except (ValueError, SyntaxError) as exc:
            raise ValidationError(_("Analytics domain must be a literal Odoo domain list.")) from exc
        if not isinstance(domain, list):
            raise ValidationError(_("Analytics domain must be a list."))
        self._analytics_validate_domain_tokens(domain)
        return domain

    def _analytics_validate_domain_tokens(self, tokens):
        allowed_boolean = {"&", "|", "!"}
        for token in tokens:
            if isinstance(token, str):
                if token not in allowed_boolean:
                    raise ValidationError(_("Unsupported token in analytics domain: %s") % token)
                continue
            if not isinstance(token, (tuple, list)) or len(token) != 3:
                raise ValidationError(_("Analytics domain leaves must contain field, operator and value."))
            field_name, operator, value = token
            if not isinstance(field_name, str) or not field_name:
                raise ValidationError(_("Analytics domain field names must be non-empty strings."))
            if field_name.startswith("__") or ";" in field_name:
                raise ValidationError(_("Unsafe analytics domain field name."))
            if not isinstance(operator, str):
                raise ValidationError(_("Analytics domain operators must be strings."))
            if callable(value):
                raise ValidationError(_("Callable values are not allowed in analytics domains."))
        return True

    def _analytics_datetime_bounds(self, period_start, period_end):
        start = datetime.combine(fields.Date.to_date(period_start), time.min)
        end = datetime.combine(fields.Date.to_date(period_end), time.max)
        return start, end

    def _analytics_json(self, payload):
        """Persist sanitized aggregate evidence only; no raw record serialization."""
        return json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, default=str)

    def _analytics_shift_date(self, value, months=0, years=0):
        value = fields.Date.to_date(value)
        return value + relativedelta(months=months, years=years)

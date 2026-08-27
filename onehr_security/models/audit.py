import json
import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

from .action_helpers import (
    open_record_action,
    require_security_admin_or_compliance,
)


class OneHRAuditLog(models.Model):
    """Append-only evidence for high-risk security actions.

    `sudo()` is intentionally confined to `_log_event()`. The business action
    must already have passed its normal ACL/record-rule/model checks. Sudo here
    only guarantees that ordinary users cannot gain create permission on the
    audit ledger merely so the application can preserve mandatory evidence.
    """

    _name = "onehr.audit.log"
    _description = "OneHR Security Audit Log"
    _inherit = ["onehr.mixin.audit"]
    _order = "event_at desc, id desc"

    event_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True, readonly=True)
    actor_user_id = fields.Many2one("res.users", required=True, ondelete="restrict", index=True, readonly=True)
    company_id = fields.Many2one("res.company", ondelete="restrict", index=True, readonly=True)

    action = fields.Selection(
        [
            ("create", "Create"),
            ("update", "Update"),
            ("activate", "Activate"),
            ("revoke", "Revoke"),
            ("reconcile", "Reconcile"),
            ("sod_detect", "SoD Detected"),
            ("sod_resolve", "SoD Resolved"),
            ("access_read", "Sensitive Read"),
            ("retention", "Retention / Anonymization"),
            ("other", "Other"),
        ],
        required=True,
        index=True,
        readonly=True,
    )
    severity = fields.Selection(
        [
            ("info", "Info"),
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        required=True,
        default="info",
        index=True,
        readonly=True,
    )

    model_name = fields.Char(index=True, readonly=True)
    res_id = fields.Integer(index=True, readonly=True)
    summary = fields.Char(required=True, readonly=True)
    changed_fields = fields.Char(readonly=True)
    before_json = fields.Text(readonly=True)
    after_json = fields.Text(readonly=True)
    metadata_json = fields.Text(readonly=True)
    correlation_id = fields.Char(required=True, index=True, readonly=True)

    role_id = fields.Many2one("onehr.role", ondelete="set null", index=True, readonly=True)
    user_role_id = fields.Many2one("onehr.user.role", ondelete="set null", index=True, readonly=True)

    is_anonymized = fields.Boolean(readonly=True)
    anonymized_at = fields.Datetime(readonly=True)
    anonymized_by_id = fields.Many2one("res.users", readonly=True)

    @api.model
    def _json_dump(self, value):
        if value in (None, False, ""):
            return False
        if isinstance(value, str):
            return value
        return json.dumps(value, default=str, sort_keys=True, ensure_ascii=False)

    @api.model
    def _log_event(
        self,
        *,
        action,
        summary,
        severity="info",
        record=None,
        company=None,
        changed_fields=None,
        before=None,
        after=None,
        metadata=None,
        role=None,
        user_role=None,
        correlation_id=None,
    ):
        """Append one audit row after business authorization has succeeded."""
        actor = self.env.user
        company = company or getattr(record, "company_id", False) or self.env.company

        values = {
            "event_at": fields.Datetime.now(),
            "actor_user_id": actor.id,
            "company_id": company.id if company else False,
            "action": action,
            "severity": severity,
            "model_name": record._name if record else False,
            "res_id": record.id if record and len(record) == 1 else False,
            "summary": summary,
            "changed_fields": ",".join(sorted(changed_fields or [])) or False,
            "before_json": self._json_dump(before),
            "after_json": self._json_dump(after),
            "metadata_json": self._json_dump(metadata),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "role_id": role.id if role else False,
            "user_role_id": user_role.id if user_role else False,
        }

        # Narrow, evidence-only sudo exception. Never use this to authorize or
        # mutate the business record that triggered the audit.
        return self.sudo().create(values)

    def write(self, vals):
        """Normal audit rows are immutable; only controlled anonymization may mutate."""
        if not self.env.context.get("onehr_audit_retention"):
            raise AccessError(_("OneHR security audit records are append-only."))

        require_security_admin_or_compliance(self.env)

        allowed = {
            "before_json",
            "after_json",
            "metadata_json",
            "summary",
            "is_anonymized",
            "anonymized_at",
            "anonymized_by_id",
        }
        if set(vals) - allowed:
            raise AccessError(_("Retention may change only approved anonymization fields."))

        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        raise AccessError(_("OneHR security audit records cannot be deleted."))

    def action_anonymize_payload(self):
        require_security_admin_or_compliance(self.env)

        for record in self:
            if record.is_anonymized:
                continue

            old_summary = record.summary
            record.with_context(onehr_audit_retention=True).write(
                {
                    "before_json": False,
                    "after_json": False,
                    "metadata_json": False,
                    "summary": _("Anonymized security event"),
                    "is_anonymized": True,
                    "anonymized_at": fields.Datetime.now(),
                    "anonymized_by_id": self.env.user.id,
                }
            )
            self._log_event(
                action="retention",
                summary=_("Audit payload anonymized"),
                severity="high",
                record=record,
                company=record.company_id,
                metadata={"previous_summary": old_summary, "audit_log_id": record.id},
            )

        return True

    def action_open_target(self):
        """Open the target only when the caller already has normal read access."""
        self.ensure_one()

        if not self.model_name or not self.res_id:
            raise UserError(_("The referenced business record is not available."))

        try:
            target_model = self.env[self.model_name]
        except KeyError as exc:
            raise UserError(_("The referenced business model is not available.")) from exc

        target = target_model.browse(self.res_id).exists()
        if not target:
            raise UserError(_("The referenced business record no longer exists."))

        target.check_access("read")

        return open_record_action(
            name=target.display_name,
            res_model=self.model_name,
            res_id=target.id,
        )

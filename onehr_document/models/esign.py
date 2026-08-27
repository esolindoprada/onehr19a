import uuid

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import (
    open_record_action,
    require_document_manager,
    require_document_manager_or_compliance,
)


TERMINAL_STATES = {"signed", "rejected", "cancelled", "error"}


class OneHREsignTransaction(models.Model):
    """Append-oriented metadata for external e-sign adapters.

    Provider credentials are intentionally absent. A soft integration addon may
    override `dispatch_to_provider()` or call `apply_provider_status()` while
    this addon remains installable without the external integration layer.
    """

    _name = "onehr.esign.transaction"
    _description = "OneHR E-Sign Transaction"
    _inherit = ["onehr.mixin.audit"]
    _order = "requested_at desc, id desc"

    _unique_correlation_id = models.UniqueIndex("(correlation_id)")

    document_version_id = fields.Many2one(
        "onehr.document.version",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        related="document_version_id.company_id",
        store=True,
        index=True,
    )
    employee_id = fields.Many2one(
        related="document_version_id.employee_id",
        store=True,
        index=True,
    )
    category_id = fields.Many2one(
        related="document_version_id.category_id",
        store=True,
        index=True,
    )
    provider_key = fields.Char(
        required=True,
        tracking=True,
        help=(
            "Non-secret adapter key, for example 'integration_queue'. "
            "No provider credential belongs in this model."
        ),
    )
    correlation_id = fields.Char(
        required=True,
        default=lambda self: str(uuid.uuid4()),
        copy=False,
        readonly=True,
        index=True,
    )
    provider_reference = fields.Char(readonly=True, index=True)
    signer_name = fields.Char(required=True, readonly=True)
    signer_email = fields.Char(required=True, readonly=True)
    message = fields.Text(readonly=True)
    state = fields.Selection(
        [
            ("queued", "Queued"),
            ("sent", "Sent"),
            ("viewed", "Viewed"),
            ("signed", "Signed"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
            ("error", "Error"),
        ],
        required=True,
        default="queued",
        index=True,
        readonly=True,
    )
    requested_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        readonly=True,
        index=True,
    )
    requested_by_id = fields.Many2one(
        "res.users",
        required=True,
        default=lambda self: self.env.user,
        ondelete="restrict",
        readonly=True,
    )
    completed_at = fields.Datetime(readonly=True)
    status_note = fields.Text(readonly=True)
    supersedes_id = fields.Many2one(
        "onehr.esign.transaction",
        ondelete="restrict",
        readonly=True,
    )
    superseded_by_id = fields.Many2one(
        "onehr.esign.transaction",
        compute="_compute_superseded_by",
        string="Superseded By",
    )

    @api.model_create_multi
    def create(self, vals_list):
        require_document_manager(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            version = self.env["onehr.document.version"].browse(
                vals.get("document_version_id")
            ).exists()
            if not version:
                raise ValidationError(
                    _("A valid document version is required.")
                )
            if version.state not in ("issued", "signature_pending"):
                raise UserError(
                    _(
                        "E-sign requests require an Issued or Signature Pending "
                        "document version."
                    )
                )
            vals.setdefault("requested_by_id", self.env.user.id)
            vals.setdefault("requested_at", fields.Datetime.now())
            vals["state"] = "queued"
            vals["correlation_id"] = (
                vals.get("correlation_id") or str(uuid.uuid4())
            )
            prepared.append(vals)

        records = super().create(prepared)
        for record in records:
            record.document_version_id.with_context(
                onehr_document_version_state_action=True
            ).write({"state": "signature_pending"})
            self.env["onehr.audit.log"]._log_event(
                action="other",
                summary=_("E-sign transaction queued"),
                severity="high",
                record=record,
                company=record.company_id,
                correlation_id=record.correlation_id,
                after={
                    "document_version_id": record.document_version_id.id,
                    "provider_key": record.provider_key,
                    "state": record.state,
                },
            )
        return records

    def write(self, vals):
        require_document_manager_or_compliance(self.env)
        if not self.env.context.get("onehr_esign_provider_update"):
            raise AccessError(
                _(
                    "E-sign transaction evidence is immutable outside the "
                    "controlled provider-status service."
                )
            )
        allowed = {
            "provider_reference",
            "state",
            "completed_at",
            "status_note",
        }
        if set(vals) - allowed:
            raise AccessError(
                _(
                    "Provider status updates may change status metadata only."
                )
            )
        if any(record.state in TERMINAL_STATES for record in self):
            raise AccessError(
                _("Terminal e-sign transactions cannot be rewritten.")
            )
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_uninstall(self):
        raise AccessError(
            _("E-sign transaction evidence cannot be deleted.")
        )

    def _compute_superseded_by(self):
        for record in self:
            record.superseded_by_id = self.search(
                [("supersedes_id", "=", record.id)],
                order="id desc",
                limit=1,
            )

    def dispatch_to_provider(self):
        """Soft-integration extension point; base addon performs no network call."""
        self.ensure_one()
        return False

    def apply_provider_status(
        self,
        *,
        state,
        provider_reference=None,
        note=None,
    ):
        """Controlled adapter API for e-sign status callbacks/polling."""
        self.ensure_one()
        require_document_manager(self.env)
        allowed_states = dict(self._fields["state"].selection)
        if state not in allowed_states:
            raise ValidationError(
                _("Unsupported e-sign status: %s", state)
            )

        values = {
            "state": state,
            "status_note": note or self.status_note,
        }
        if provider_reference:
            values["provider_reference"] = provider_reference
        if state in TERMINAL_STATES:
            values["completed_at"] = fields.Datetime.now()

        self.with_context(onehr_esign_provider_update=True).write(values)

        version = self.document_version_id
        if state == "signed" and version.state in (
            "issued",
            "signature_pending",
        ):
            version.with_context(
                onehr_document_version_state_action=True
            ).write(
                {
                    "state": "signed",
                    "signed_at": fields.Datetime.now(),
                    "signed_by_id": self.env.user.id,
                }
            )

        self.env["onehr.audit.log"]._log_event(
            action="other",
            summary=_("E-sign status updated to %s", state),
            severity="high",
            record=self,
            company=self.company_id,
            correlation_id=self.correlation_id,
            changed_fields={
                "state",
                "provider_reference",
                "status_note",
            },
            after={
                "state": self.state,
                "provider_reference": self.provider_reference,
            },
        )
        return True

    def action_cancel(self):
        require_document_manager(self.env)
        for record in self:
            if record.state in TERMINAL_STATES:
                raise UserError(
                    _(
                        "Terminal e-sign transactions cannot be cancelled."
                    )
                )
            record.apply_provider_status(
                state="cancelled",
                note=_("Cancelled by document manager"),
            )
        return True

    def action_open_document_version(self):
        self.ensure_one()
        return open_record_action(
            name=self.document_version_id.display_name,
            res_model="onehr.document.version",
            res_id=self.document_version_id.id,
        )

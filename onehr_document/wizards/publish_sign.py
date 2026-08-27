from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError

from ..models.action_helpers import (
    open_record_action,
    require_document_manager,
)


class WizardDocumentPublishSign(models.TransientModel):
    _name = "wizard.document.publish.sign"
    _description = "Publish / Request Document Signature"

    document_id = fields.Many2one(
        "onehr.document",
        required=True,
        ondelete="cascade",
    )
    document_version_id = fields.Many2one(
        "onehr.document.version",
        required=True,
        ondelete="cascade",
    )
    provider_key = fields.Char(
        required=True,
        default="integration_queue",
        help=(
            "Non-secret adapter key. Credentials remain outside "
            "onehr_document."
        ),
    )
    signer_name = fields.Char(required=True)
    signer_email = fields.Char(required=True)
    message = fields.Text()
    dispatch_now = fields.Boolean(
        default=True,
        help=(
            "Calls the soft integration hook after the transaction is queued. "
            "The base addon itself performs no network call."
        ),
    )

    def action_submit(self):
        self.ensure_one()
        require_document_manager(self.env)

        if self.document_version_id.document_id != self.document_id:
            raise ValidationError(
                _("Document Version must belong to the selected Document.")
            )
        if self.document_version_id.state not in (
            "issued",
            "signature_pending",
        ):
            raise UserError(
                _(
                    "Only Issued or Signature Pending versions can be sent "
                    "for signature."
                )
            )

        transaction = self.env["onehr.esign.transaction"].create(
            {
                "document_version_id": self.document_version_id.id,
                "provider_key": self.provider_key.strip(),
                "signer_name": self.signer_name.strip(),
                "signer_email": self.signer_email.strip(),
                "message": self.message,
            }
        )
        if self.dispatch_now:
            transaction.dispatch_to_provider()

        return open_record_action(
            name=transaction.display_name,
            res_model="onehr.esign.transaction",
            res_id=transaction.id,
        )

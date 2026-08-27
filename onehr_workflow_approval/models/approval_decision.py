from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action
from .routing_helpers import require_workflow_admin


class OneHRApprovalDecision(models.Model):
    _name = "onehr.approval.decision"
    _description = "OneHR Immutable Approval Decision"
    _inherit = ["onehr.mixin.audit"]
    _order = "decided_at desc, id desc"

    request_id = fields.Many2one(
        "onehr.approval.request", required=True, ondelete="cascade", index=True
    )
    step_id = fields.Many2one("onehr.approval.step", ondelete="restrict", index=True)
    company_id = fields.Many2one(related="request_id.company_id", store=True, index=True)

    approver_id = fields.Many2one(
        "res.users",
        ondelete="restrict",
        index=True,
        readonly=True,
        help="Actor who recorded this decision.",
    )
    authority_user_id = fields.Many2one(
        "res.users",
        ondelete="restrict",
        index=True,
        readonly=True,
        help=(
            "Underlying authority identity represented by this decision. "
            "For delegation/reassignment it can differ from the acting approver."
        ),
    )
    decision = fields.Selection(
        [("approve", "Approve"), ("reject", "Reject")],
        required=True,
        index=True,
        readonly=True,
    )
    rationale = fields.Text(readonly=True)
    decided_at = fields.Datetime(
        required=True,
        default=fields.Datetime.now,
        index=True,
        readonly=True,
    )
    decision_source = fields.Selection(
        [
            ("human", "Human"),
            ("delegated", "Delegated"),
            ("reassigned", "Reassigned"),
            ("escalated", "Escalated"),
            ("automatic", "Automatic Rule"),
            ("correction", "Correction"),
        ],
        required=True,
        default="human",
        readonly=True,
    )

    delegated_from_user_id = fields.Many2one("res.users", ondelete="restrict", readonly=True)
    delegation_id = fields.Many2one("onehr.approval.delegate", ondelete="restrict", readonly=True)

    supersedes_id = fields.Many2one(
        "onehr.approval.decision", ondelete="restrict", index=True, readonly=True
    )
    correction_ids = fields.One2many(
        "onehr.approval.decision", "supersedes_id", string="Corrections", readonly=True
    )
    correction_reason = fields.Text(readonly=True)
    is_correction = fields.Boolean(readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get("onehr_approval_engine"):
            raise AccessError(
                _("Approval decisions must be recorded through controlled approval request actions.")
            )

        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            request = self.env["onehr.approval.request"].browse(values.get("request_id")).exists()
            if not request:
                raise ValidationError(_("A valid approval request is required."))

            if values.get("is_correction"):
                require_workflow_admin(self.env)
                supersedes = self.browse(values.get("supersedes_id")).exists()
                if not supersedes or supersedes.request_id != request:
                    raise ValidationError(
                        _("A correction must supersede a decision on the same request.")
                    )
                values.update(
                    {
                        "approver_id": self.env.user.id,
                        "authority_user_id": supersedes.authority_user_id.id,
                        "decision_source": "correction",
                        "decided_at": fields.Datetime.now(),
                    }
                )
            elif values.get("decision_source") == "automatic":
                if not request.rule_id.auto_approve:
                    raise AccessError(
                        _("Automatic decision is allowed only for an automatic approval rule.")
                    )
                values.update(
                    {
                        "approver_id": False,
                        "authority_user_id": False,
                        "decided_at": fields.Datetime.now(),
                    }
                )
            else:
                if request.state != "pending":
                    raise UserError(_("Human decisions can only be recorded on a pending request."))
                if values.get("decision") == "reject" and not values.get("rationale"):
                    raise UserError(_("A rejection rationale is mandatory."))
                step = self.env["onehr.approval.step"].browse(values.get("step_id")).exists()
                if not step or step not in request.current_step_ids:
                    raise AccessError(_("Decision step is not active on the request."))

                identity = request._decision_identity_for_user(step, self.env.user)
                if not identity:
                    raise AccessError(_("You are not an eligible approver for this step."))
                values.update(identity)
                values["approver_id"] = self.env.user.id
                values["decided_at"] = fields.Datetime.now()

                existing = request._effective_decisions(step).filtered(
                    lambda item: item.authority_user_id.id == values["authority_user_id"]
                )
                if existing:
                    raise UserError(
                        _("This approval authority already has an effective decision for the step.")
                    )

            prepared.append(values)

        records = super().create(prepared)
        for record in records:
            self.env["onehr.audit.log"]._log_event(
                action="other",
                summary=_(
                    "Approval decision %(decision)s on %(request)s",
                    decision=record.decision,
                    request=record.request_id.display_name,
                ),
                severity="high",
                record=record,
                company=record.company_id,
                metadata={
                    "workflow_event": "approval_decision",
                    "decision": record.decision,
                    "request_id": record.request_id.id,
                    "step_id": record.step_id.id,
                    "authority_user_id": record.authority_user_id.id,
                    "decision_source": record.decision_source,
                    "supersedes_id": record.supersedes_id.id,
                },
            )
        return records

    def write(self, vals):
        raise AccessError(
            _(
                "Approval decisions are immutable. Record a superseding correction "
                "instead of rewriting decision evidence."
            )
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_immutable_decisions(self):
        raise AccessError(_("Approval decision evidence cannot be deleted."))

    def record_correction(self, new_decision, reason):
        """Create immutable superseding evidence; never rewrite the original row."""
        require_workflow_admin(self.env)
        self.ensure_one()
        if new_decision not in {"approve", "reject"}:
            raise ValidationError(_("Correction decision must be approve or reject."))
        if not reason:
            raise ValidationError(_("A correction reason is mandatory."))

        latest = self
        while latest.correction_ids:
            latest = latest.correction_ids.sorted(lambda item: (item.decided_at, item.id))[-1]

        correction = self.with_context(onehr_approval_engine=True).create(
            {
                "request_id": self.request_id.id,
                "step_id": self.step_id.id,
                "decision": new_decision,
                "rationale": reason,
                "is_correction": True,
                "supersedes_id": latest.id,
                "correction_reason": reason,
            }
        )

        if self.request_id.state == "pending":
            self.request_id._evaluate_current_level()
        else:
            self.request_id.message_post(
                body=_(
                    "Decision evidence correction recorded after workflow finalization. "
                    "The source transaction was not silently rewritten."
                )
            )
        return correction

    def action_open_request(self):
        self.ensure_one()
        return open_record_action(
            name=self.request_id.display_name,
            res_model="onehr.approval.request",
            res_id=self.request_id.id,
        )

    def action_open_source(self):
        self.ensure_one()
        return self.request_id.action_open_source()

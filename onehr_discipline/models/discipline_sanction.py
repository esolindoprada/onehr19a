
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    open_record_action,
    require_hrbp,
    require_legal,
)


class OneHRDisciplineSanction(models.Model):
    """Governed disciplinary decision and sanction execution.

    OneHR Workflow Approval owns routing and approval evidence. Discipline owns
    the sanction business state and executes/serves the approved decision only
    after the workflow request is finalized.
    """

    _name = "onehr.discipline.sanction"
    _description = "OneHR Discipline Sanction / Decision"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "decision_date desc, id desc"

    _reference_company_uniq = models.Constraint(
        "UNIQUE(reference, company_id)",
        "Sanction reference must be unique per company.",
    )

    reference = fields.Char(
        string="Sanction Reference",
        required=True,
        default="New",
        readonly=True,
        copy=False,
        tracking=True,
        index=True,
    )
    case_id = fields.Many2one(
        "onehr.discipline.case",
        required=True,
        ondelete="restrict",
        readonly=True,
        tracking=True,
        index=True,
    )
    case_reference = fields.Char(
        related="case_id.reference",
        store=True,
        readonly=True,
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        related="case_id.company_id",
        store=True,
        readonly=True,
        index=True,
    )
    branch_scope_key = fields.Char(
        related="case_id.branch_scope_key",
        store=True,
        readonly=True,
        index=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        related="case_id.employee_id",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups=(
            "onehr_discipline.group_onehr_discipline_hrbp,"
            "onehr_discipline.group_onehr_discipline_manager,"
            "onehr_discipline.group_onehr_discipline_legal"
        ),
    )
    employee_number = fields.Char(
        related="case_id.employee_number",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        groups=(
            "onehr_discipline.group_onehr_discipline_hrbp,"
            "onehr_discipline.group_onehr_discipline_manager,"
            "onehr_discipline.group_onehr_discipline_legal"
        ),
    )
    employee_name = fields.Char(
        related="case_id.employee_name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
        string="Employee",
    )
    department_name = fields.Char(
        related="case_id.department_name",
        store=True,
        compute_sudo=True,
        readonly=True,
        index=True,
    )

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approval", "Approval"),
            ("approved", "Approved"),
            ("executed", "Executed / Issued"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        required=True,
        default="draft",
        readonly=True,
        tracking=True,
        index=True,
    )
    sanction_type = fields.Selection(
        [
            ("no_action", "No Disciplinary Action"),
            ("verbal_warning", "Verbal Warning"),
            ("written_warning", "Written Warning"),
            ("sp1", "SP-1 / First Written Warning"),
            ("sp2", "SP-2 / Second Written Warning"),
            ("sp3", "SP-3 / Final Written Warning"),
            ("suspension", "Suspension"),
            ("probation", "Probation / Performance Conduct Period"),
            ("payroll_deduction", "Payroll Deduction Request"),
            ("last_chance", "Last Chance Agreement"),
            ("termination", "Termination Recommendation"),
            ("other", "Other Disciplinary Measure"),
        ],
        required=True,
        default="written_warning",
        tracking=True,
        index=True,
    )
    severity = fields.Selection(
        related="case_id.severity",
        store=True,
        readonly=True,
        index=True,
    )
    decision_date = fields.Date(
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        index=True,
    )
    effective_start_date = fields.Date(
        tracking=True,
        index=True,
    )
    effective_end_date = fields.Date(
        tracking=True,
        index=True,
    )
    warning_expiry_date = fields.Date(
        tracking=True,
        index=True,
    )
    decision_basis = fields.Html(
        sanitize=True,
        tracking=True,
        required=True,
    )
    legal_basis = fields.Html(
        sanitize=True,
        tracking=True,
    )
    sanction_terms = fields.Html(
        sanitize=True,
        tracking=True,
    )
    manager_expectations = fields.Html(
        sanitize=True,
        tracking=True,
    )
    followup_review_date = fields.Date(
        tracking=True,
        index=True,
    )

    probation_start_date = fields.Date(
        tracking=True,
    )
    probation_end_date = fields.Date(
        tracking=True,
    )
    probation_conditions = fields.Html(
        sanitize=True,
        tracking=True,
    )

    payroll_deduction_amount = fields.Monetary(
        tracking=True,
        currency_field="currency_id",
        help=(
            "Discipline-owned approved amount request. "
            "Payroll execution remains owned by Payroll Bridge/payroll."
        ),
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    payroll_period_date = fields.Date(
        tracking=True,
        help="Target payroll period anchor; downstream Payroll Bridge owns actual posting.",
    )
    payroll_execution_state = fields.Selection(
        [
            ("not_applicable", "Not Applicable"),
            ("pending", "Pending Payroll Adapter"),
            ("exported", "Exported to Payroll"),
            ("confirmed", "Confirmed by Payroll"),
            ("rejected", "Rejected by Payroll"),
        ],
        required=True,
        default="not_applicable",
        readonly=True,
        tracking=True,
        index=True,
    )
    payroll_execution_reference = fields.Char(
        readonly=True,
        copy=False,
        tracking=True,
    )

    contract_action = fields.Selection(
        [
            ("none", "No Contract Action"),
            ("probation", "Probation Review"),
            ("termination", "Termination Recommendation"),
            ("other", "Other Contract Review"),
        ],
        required=True,
        default="none",
        tracking=True,
    )
    contract_reference = fields.Char(
        tracking=True,
        help=(
            "Soft reference to an Employment Contract record/document. "
            "No contract lifecycle is mutated by this addon."
        ),
    )
    document_archive_reference = fields.Char(
        tracking=True,
        help=(
            "Optional OneHR Document reference written by an approved downstream adapter."
        ),
    )

    decision_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_disc_sanction_decision_rel",
        "sanction_id",
        "attachment_id",
        string="Decision / Supporting Attachments",
        copy=False,
    )
    execution_attachment_ids = fields.Many2many(
        "ir.attachment",
        "onehr_disc_sanction_execution_rel",
        "sanction_id",
        "attachment_id",
        string="Execution / Service Evidence",
        copy=False,
    )

    approval_request_id = fields.Many2one(
        "onehr.approval.request",
        string="Finalized Approval",
        ondelete="restrict",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approval_finalized_at = fields.Datetime(
        readonly=True,
        copy=False,
    )
    approved_at = fields.Datetime(
        readonly=True,
        copy=False,
    )
    approved_by_name = fields.Char(
        readonly=True,
        copy=False,
    )
    rejected_at = fields.Datetime(
        readonly=True,
        copy=False,
    )
    rejected_by_name = fields.Char(
        readonly=True,
        copy=False,
    )

    executed_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
    )
    executed_by_name = fields.Char(
        readonly=True,
        copy=False,
    )
    execution_note = fields.Text(
        tracking=True,
    )
    served_at = fields.Datetime(
        readonly=True,
        copy=False,
        tracking=True,
    )
    served_by_name = fields.Char(
        readonly=True,
        copy=False,
    )
    employee_receipt_acknowledged = fields.Boolean(
        readonly=True,
        copy=False,
        tracking=True,
    )
    employee_receipt_note = fields.Text(
        tracking=True,
    )

    appeal_state = fields.Selection(
        related="case_id.appeal_state",
        store=True,
        readonly=True,
        index=True,
    )

    _DEFINITION_FIELDS = {
        "sanction_type",
        "decision_date",
        "effective_start_date",
        "effective_end_date",
        "warning_expiry_date",
        "decision_basis",
        "legal_basis",
        "sanction_terms",
        "manager_expectations",
        "followup_review_date",
        "probation_start_date",
        "probation_end_date",
        "probation_conditions",
        "payroll_deduction_amount",
        "payroll_period_date",
        "contract_action",
        "contract_reference",
        "decision_attachment_ids",
    }
    _EXECUTION_EVIDENCE_FIELDS = {
        "execution_note",
        "execution_attachment_ids",
        "employee_receipt_note",
    }
    _ACTION_ONLY_FIELDS = {
        "reference",
        "case_id",
        "state",
        "payroll_execution_state",
        "payroll_execution_reference",
        "document_archive_reference",
        "approval_request_id",
        "approval_finalized_at",
        "approved_at",
        "approved_by_name",
        "rejected_at",
        "rejected_by_name",
        "executed_at",
        "executed_by_name",
        "served_at",
        "served_by_name",
        "employee_receipt_acknowledged",
    }

    @api.model_create_multi
    def create(self, vals_list):
        require_hrbp(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            case = self.env["onehr.discipline.case"].browse(
                vals.get("case_id")
            ).exists()
            if not case:
                raise ValidationError(
                    _("A valid Discipline Case is required.")
                )
            if case.state != "decision":
                raise UserError(
                    _("A sanction/decision can be created only while the Case is in Decision.")
                )
            if vals.get("reference", "New") == "New":
                vals["reference"] = (
                    self.env["ir.sequence"].next_by_code(
                        "onehr.discipline.sanction"
                    )
                    or "New"
                )
            vals["state"] = "draft"
            vals["payroll_execution_state"] = (
                "pending"
                if vals.get("sanction_type") == "payroll_deduction"
                else "not_applicable"
            )
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        require_hrbp(self)
        requested = set(vals)
        if requested.intersection(self._ACTION_ONLY_FIELDS):
            raise AccessError(
                _("Sanction lifecycle and external execution evidence change only through governed actions/services.")
            )

        for sanction in self:
            if (
                sanction.state not in ("draft", "rejected")
                and requested.intersection(self._DEFINITION_FIELDS)
            ):
                raise AccessError(
                    _(
                        "Approved/submitted sanction definition is immutable. "
                        "Use the approval/rejection lifecycle rather than rewriting decision evidence."
                    )
                )
            if requested.intersection(
                self._EXECUTION_EVIDENCE_FIELDS
            ) and sanction.state != "executed":
                raise AccessError(
                    _("Execution/service evidence may be edited only after the sanction is Executed.")
                )

            if sanction.state in ("executed", "cancelled"):
                allowed_after_execution = {
                    "employee_receipt_note",
                    "execution_attachment_ids",
                }
                if requested - allowed_after_execution:
                    raise AccessError(
                        _("Executed/Cancelled sanctions are historical records and cannot be rewritten.")
                    )
        result = super().write(vals)
        if "sanction_type" in requested:
            for sanction in self:
                sanction._write_action(
                    {
                        "payroll_execution_state": (
                            "pending"
                            if sanction.sanction_type
                            == "payroll_deduction"
                            else "not_applicable"
                        ),
                        "payroll_execution_reference": False,
                    }
                )
        return result

    def _write_action(self, values):
        """Internal sanction lifecycle write without spoofable context bypass."""
        return super(OneHRDisciplineSanction, self).write(values)

    @api.constrains(
        "effective_start_date",
        "effective_end_date",
        "warning_expiry_date",
        "probation_start_date",
        "probation_end_date",
    )
    def _check_dates(self):
        for sanction in self:
            if (
                sanction.effective_start_date
                and sanction.effective_end_date
                and sanction.effective_end_date
                < sanction.effective_start_date
            ):
                raise ValidationError(
                    _("Effective End Date cannot be earlier than Effective Start Date.")
                )
            if (
                sanction.probation_start_date
                and sanction.probation_end_date
                and sanction.probation_end_date
                < sanction.probation_start_date
            ):
                raise ValidationError(
                    _("Probation End Date cannot be earlier than Probation Start Date.")
                )

    @api.constrains(
        "sanction_type",
        "payroll_deduction_amount",
        "probation_start_date",
        "probation_end_date",
        "contract_action",
    )
    def _check_sanction_requirements(self):
        for sanction in self:
            if (
                sanction.sanction_type == "payroll_deduction"
                and sanction.payroll_deduction_amount <= 0
            ):
                raise ValidationError(
                    _("Payroll Deduction Request requires a positive approved amount.")
                )
            if sanction.sanction_type in ("probation", "last_chance"):
                if (
                    not sanction.probation_start_date
                    or not sanction.probation_end_date
                    or not sanction.probation_conditions
                ):
                    raise ValidationError(
                        _(
                            "Probation / Last Chance sanction requires start date, end date and conditions."
                        )
                    )
            if (
                sanction.sanction_type == "termination"
                and sanction.contract_action != "termination"
            ):
                raise ValidationError(
                    _("Termination Recommendation must use Contract Action = Termination Recommendation.")
                )

    def _required_before_approval(self):
        self.ensure_one()
        missing = []
        if not self.decision_basis:
            missing.append(_("Decision Basis"))
        if self.sanction_type in (
            "written_warning",
            "sp1",
            "sp2",
            "sp3",
            "suspension",
            "probation",
            "last_chance",
            "termination",
            "other",
        ) and not self.sanction_terms:
            missing.append(_("Sanction Terms"))
        if self.sanction_type == "payroll_deduction":
            if self.payroll_deduction_amount <= 0:
                missing.append(_("Payroll Deduction Amount"))
            if not self.payroll_period_date:
                missing.append(_("Payroll Period Date"))
        return missing

    def _approval_payload(self):
        self.ensure_one()
        return {
            "sanction_reference": self.reference,
            "case_reference": self.case_reference,
            "employee_number": self.employee_number,
            "sanction_type": self.sanction_type,
            "severity": self.severity,
            "decision_date": str(self.decision_date or ""),
            "effective_start_date": str(self.effective_start_date or ""),
            "effective_end_date": str(self.effective_end_date or ""),
            "payroll_deduction_amount": self.payroll_deduction_amount,
            "currency_id": self.currency_id.id,
            "contract_action": self.contract_action,
        }

    def _approval_branch_scope_key(self):
        self.ensure_one()
        return self.branch_scope_key or False

    def _approval_rule_context(self):
        self.ensure_one()
        context = super()._approval_rule_context()
        risk_map = {
            "minor": "low",
            "moderate": "normal",
            "serious": "high",
            "critical": "critical",
        }
        manager_user_ids = []
        if self.case_id.employee_id.parent_id.user_id:
            manager_user_ids = [
                self.case_id.employee_id.parent_id.user_id.id
            ]
        context.update(
            {
                "company_id": self.company_id.id,
                "branch_scope_key": self._approval_branch_scope_key(),
                "document_type": (
                    f"onehr.discipline.sanction.{self.sanction_type}"
                ),
                "amount": (
                    self.payroll_deduction_amount
                    if self.sanction_type == "payroll_deduction"
                    else 0.0
                ),
                "currency_id": self.currency_id.id,
                "risk_level": risk_map.get(
                    self.severity,
                    "normal",
                ),
                "manager_user_ids": manager_user_ids,
                "approver_user_ids_by_key": {
                    "discipline_legal": (
                        [self.case_id.legal_user_id.id]
                        if self.case_id.legal_user_id
                        else []
                    ),
                    "discipline_hrbp": (
                        [self.case_id.hrbp_user_id.id]
                        if self.case_id.hrbp_user_id
                        else []
                    ),
                },
                "extra": {
                    "case_reference": self.case_reference,
                    "sanction_type": self.sanction_type,
                    "severity": self.severity,
                    "violation_category": self.case_id.violation_category,
                    "repeat_offense": bool(
                        self.case_id.repeat_offense
                    ),
                },
            }
        )
        return context

    def _approval_cancel_guard(self, request):
        self.ensure_one()
        return self.state in ("approval", "rejected", "draft")

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "approval":
            raise UserError(
                _("Sanction approval finalized while the sanction is not in Approval state.")
            )

        now = fields.Datetime.now()
        if decision == "approve":
            self._write_action(
                {
                    "state": "approved",
                    "approval_request_id": request.id,
                    "approval_finalized_at": now,
                    "approved_at": now,
                    "approved_by_name": self.env.user.name,
                    "rejected_at": False,
                    "rejected_by_name": False,
                }
            )
        elif decision == "reject":
            self._write_action(
                {
                    "state": "rejected",
                    "approval_request_id": request.id,
                    "approval_finalized_at": now,
                    "approved_at": False,
                    "approved_by_name": False,
                    "rejected_at": now,
                    "rejected_by_name": self.env.user.name,
                }
            )
        else:
            raise ValidationError(
                _("Unsupported Discipline approval decision.")
            )
        return True

    def action_submit_for_sanction_approval(self):
        require_hrbp(self)
        self.ensure_one()
        if self.state not in ("draft", "rejected"):
            raise UserError(
                _("Only Draft or Rejected sanctions can be submitted for approval.")
            )
        if self.case_id.state != "decision":
            raise UserError(
                _("The parent Case must remain in Decision while a sanction is approved.")
            )

        if not self.case_id.decision_summary:
            raise UserError(
                _("Complete the Case Decision Summary before sanction approval.")
            )
        if self.case_id.final_disposition == "pending":
            raise UserError(
                _("Select the Case Final Disposition before sanction approval.")
            )
        if (
            self.sanction_type != "no_action"
            and self.case_id.final_disposition != "sanction"
        ):
            raise UserError(
                _(
                    "A formal sanction requires Case Final Disposition = Formal Sanction "
                    "before approval."
                )
            )
        if self.case_id.appeal_state in ("submitted", "review"):
            raise UserError(
                _("Resolve the active appeal before submitting a sanction approval.")
            )

        missing = self._required_before_approval()
        if missing:
            raise UserError(
                _("Sanction approval blocked. Complete: %s")
                % ", ".join(missing)
            )

        active_request = self.env["onehr.approval.request"].search(
            [
                ("source_model", "=", self._name),
                ("source_res_id", "=", self.id),
                ("state", "in", ["draft", "submitted", "pending"]),
            ],
            limit=1,
        )
        if active_request:
            raise UserError(
                _("An active OneHR Workflow Approval request already exists.")
            )

        self._write_action(
            {
                "state": "approval",
                "approval_request_id": False,
                "approval_finalized_at": False,
                "approved_at": False,
                "approved_by_name": False,
                "rejected_at": False,
                "rejected_by_name": False,
            }
        )
        return self.action_submit_for_approval()

    def action_return_to_draft(self):
        require_legal(self)
        for sanction in self:
            if sanction.state != "rejected":
                raise UserError(
                    _("Only a Rejected sanction can return to Draft.")
                )
            sanction._write_action(
                {
                    "state": "draft",
                    "approval_request_id": False,
                    "approval_finalized_at": False,
                    "rejected_at": False,
                    "rejected_by_name": False,
                }
            )
        return display_notification(
            _("Rejected sanction returned to Draft."),
            notification_type="warning",
        )

    def action_execute(self):
        require_legal(self)
        for sanction in self:
            if sanction.state != "approved":
                raise UserError(
                    _("Only an Approved sanction can be executed/issued.")
                )
            request = sanction.approval_request_id
            if (
                not request
                or request.state != "approved"
                or request.final_decision != "approve"
            ):
                raise UserError(
                    _("A finalized approved OneHR Workflow request is required before execution.")
                )
            if sanction.case_id.state != "decision":
                raise UserError(
                    _("The parent case must remain in Decision until the approved sanction is executed.")
                )

            sanction._write_action(
                {
                    "state": "executed",
                    "executed_at": fields.Datetime.now(),
                    "executed_by_name": self.env.user.name,
                    "payroll_execution_state": (
                        "pending"
                        if sanction.sanction_type
                        == "payroll_deduction"
                        else "not_applicable"
                    ),
                }
            )
            sanction.onehr_mark_approval_executed(request)
        return display_notification(
            _("Approved sanction executed/issued. Downstream payroll/contract actions remain with their owning modules.")
        )

    def action_mark_served(self):
        require_hrbp(self)
        for sanction in self:
            if sanction.state != "executed":
                raise UserError(
                    _("Employee service/receipt can be recorded only after execution/issuance.")
                )
            sanction._write_action(
                {
                    "served_at": fields.Datetime.now(),
                    "served_by_name": self.env.user.name,
                    "employee_receipt_acknowledged": True,
                }
            )
        return display_notification(
            _("Employee service/receipt evidence recorded.")
        )

    def action_cancel(self):
        require_legal(self)
        for sanction in self:
            if sanction.state not in ("draft", "rejected"):
                raise UserError(
                    _("Only Draft/Rejected sanctions can be Cancelled.")
                )
            sanction._write_action({"state": "cancelled"})
        return display_notification(
            _("Sanction cancelled; decision history remains available."),
            notification_type="warning",
        )

    def action_open_case(self):
        self.ensure_one()
        return open_record_action(
            name=_("Discipline Case"),
            res_model="onehr.discipline.case",
            res_id=self.case_id.id,
        )

    def action_print_sanction_letter(self):
        self.ensure_one()
        if self.state not in ("approved", "executed"):
            raise UserError(
                _("Sanction letters may be printed only after approval.")
            )
        return self.env.ref(
            "onehr_discipline.action_report_discipline_sanction_letter"
        ).report_action(self)

    def action_print_decision_record(self):
        self.ensure_one()
        return self.env.ref(
            "onehr_discipline.action_report_discipline_decision_record"
        ).report_action(self)

    @api.model
    def onehr_record_payroll_execution(
        self,
        sanction_reference,
        execution_state,
        execution_reference=None,
    ):
        """Narrow downstream adapter callback.

        It records external execution evidence only. Payroll calculation/posting
        remains entirely outside Discipline ownership.
        """
        require_legal(self)
        allowed_states = {
            "pending",
            "exported",
            "confirmed",
            "rejected",
        }
        if execution_state not in allowed_states:
            raise ValidationError(
                _("Unsupported payroll execution state.")
            )
        sanction = self.search(
            [
                ("reference", "=", sanction_reference),
                ("company_id", "in", self.env.companies.ids),
            ],
            limit=2,
        )
        if len(sanction) != 1:
            raise ValidationError(
                _("Sanction reference must resolve to exactly one allowed record.")
            )
        if (
            sanction.sanction_type != "payroll_deduction"
            or sanction.state != "executed"
        ):
            raise UserError(
                _("Payroll execution evidence requires an Executed Payroll Deduction sanction.")
            )
        sanction._write_action(
            {
                "payroll_execution_state": execution_state,
                "payroll_execution_reference": (
                    execution_reference or False
                ),
            }
        )
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_only_unsubmitted_draft(self):
        require_legal(self)
        for sanction in self:
            if (
                sanction.state not in ("draft", "rejected")
                or sanction.onehr_approval_request_count
            ):
                raise UserError(
                    _(
                        "Only an unsubmitted Draft/Rejected sanction may be deleted. "
                        "Approved/executed approval evidence is retained."
                    )
                )


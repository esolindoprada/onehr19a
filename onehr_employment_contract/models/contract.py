from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import open_record_action, open_records_action
from .authority_helpers import require_contract_manager, require_contract_officer


class OneHRContract(models.Model):
    """Legal/workflow wrapper around Odoo's canonical hr.version contract facts.

    Live dates, trial end and wage stay on hr.version. This record stores legal
    workflow/evidence, immutable approval snapshots, renewal/termination evidence,
    reminder state and cross-domain orchestration links.
    """

    _name = "onehr.contract"
    _description = "OneHR Employment Contract Governance"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "id desc"

    name = fields.Char(
        string="Contract Number", required=True, readonly=True, copy=False,
        default=lambda self: _("New"), index=True, tracking=True,
    )
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        index=True, ondelete="restrict", tracking=True,
    )
    employee_id = fields.Many2one(
        "hr.employee", required=True, index=True, ondelete="restrict",
        check_company=True, tracking=True,
    )
    employee_name = fields.Char(
        related="employee_id.name",
        string="Employee",
        readonly=True,
        help="Controlled display field used by line managers without exposing the private hr.employee model.",
    )
    hr_version_id = fields.Many2one(
        "hr.version", string="Native HR Version", required=True, index=True,
        ondelete="restrict", groups="onehr_employment_contract.group_onehr_contract_officer",
        tracking=True,
        help="Canonical Odoo employment/contract facts remain owned by hr.version.",
    )
    template_id = fields.Many2one(
        "onehr.contract.template", required=True, index=True, ondelete="restrict", tracking=True,
    )
    template_name = fields.Char(
        related="template_id.name",
        string="Contract Template",
        readonly=True,
        help="Display-only template label for users who are not allowed to browse contract-template configuration.",
    )
    responsible_user_id = fields.Many2one(
        "res.users", required=True, default=lambda self: self.env.user,
        ondelete="restrict", tracking=True,
    )
    contract_kind = fields.Selection(
        [("initial", "Initial"), ("renewal", "Renewal"), ("amendment", "Amendment")],
        required=True, default="initial", index=True, tracking=True,
    )
    predecessor_contract_id = fields.Many2one(
        "onehr.contract", ondelete="restrict", index=True, tracking=True,
    )
    successor_contract_ids = fields.One2many(
        "onehr.contract", "predecessor_contract_id", string="Successor Contracts",
    )
    successor_count = fields.Integer(compute="_compute_successor_count", string="Successors")

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("in_review", "In Review"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("terminated", "Terminated"),
        ],
        required=True, default="draft", index=True, copy=False, tracking=True,
    )
    pending_approval_kind = fields.Selection(
        [("contract", "Contract Approval"), ("termination", "Termination Approval")],
        copy=False, readonly=True, tracking=True,
    )
    approved_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    activated_at = fields.Datetime(readonly=True, copy=False, tracking=True)
    activated_by_id = fields.Many2one("res.users", readonly=True, copy=False)

    # Live canonical values: non-stored related fields deliberately avoid a
    # second source of truth.
    native_date_version = fields.Date(related="hr_version_id.date_version", string="Version Effective", readonly=True)
    native_contract_start = fields.Date(related="hr_version_id.contract_date_start", string="Contract Start", readonly=True)
    native_contract_end = fields.Date(related="hr_version_id.contract_date_end", string="Contract End", readonly=True)
    native_trial_end = fields.Date(related="hr_version_id.trial_date_end", string="Trial End", readonly=True)
    native_contract_wage = fields.Monetary(
        related="hr_version_id.contract_wage", string="Contract Wage", readonly=True,
        currency_field="currency_id", groups="onehr_employment_contract.group_onehr_contract_officer",
    )
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    native_job_id = fields.Many2one(related="hr_version_id.job_id", string="Job", readonly=True)
    native_department_id = fields.Many2one(related="hr_version_id.department_id", string="Department", readonly=True)
    native_work_location_id = fields.Many2one(related="hr_version_id.work_location_id", string="Work Location", readonly=True)
    native_engagement_type_id = fields.Many2one(
        related="hr_version_id.onehr_engagement_type_id", string="Engagement Type", readonly=True,
    )
    native_grade_id = fields.Many2one(related="hr_version_id.onehr_grade_id", string="Grade", readonly=True)
    native_position_id = fields.Many2one(related="hr_version_id.onehr_primary_position_id", string="Position", readonly=True)
    native_engagement_type_name = fields.Char(
        related="hr_version_id.onehr_engagement_type_id.name",
        string="Engagement Type",
        readonly=True,
    )
    native_grade_name = fields.Char(
        related="hr_version_id.onehr_grade_id.name",
        string="Grade",
        readonly=True,
    )
    native_position_name = fields.Char(
        related="hr_version_id.onehr_primary_position_id.name",
        string="Position",
        readonly=True,
    )

    # Frozen ED3 legal snapshot captured at submission. These fields are
    # evidence, not canonical employment masters.
    snapshot_contract_start = fields.Date(readonly=True, copy=False)
    snapshot_contract_end = fields.Date(readonly=True, copy=False)
    snapshot_trial_end = fields.Date(readonly=True, copy=False)
    snapshot_contract_wage = fields.Monetary(
        readonly=True, copy=False, currency_field="snapshot_currency_id",
        groups="onehr_employment_contract.group_onehr_contract_officer",
    )
    snapshot_currency_id = fields.Many2one("res.currency", readonly=True, copy=False)
    snapshot_job_name = fields.Char(readonly=True, copy=False)
    snapshot_department_name = fields.Char(readonly=True, copy=False)
    snapshot_position_name = fields.Char(readonly=True, copy=False)
    snapshot_grade_name = fields.Char(readonly=True, copy=False)
    snapshot_engagement_type_name = fields.Char(readonly=True, copy=False)
    snapshot_template_code = fields.Char(readonly=True, copy=False)
    snapshot_template_version = fields.Integer(readonly=True, copy=False)

    expiry_reminder_lead_days = fields.Integer(default=30, tracking=True)
    expiry_reminder_sent_at = fields.Datetime(readonly=True, copy=False)
    days_to_expiry = fields.Integer(compute="_compute_days_to_expiry")

    termination_type = fields.Selection(
        [
            ("resignation", "Resignation"),
            ("employer_termination", "Employer Termination"),
            ("mutual", "Mutual Agreement"),
            ("retirement", "Retirement"),
            ("other", "Other"),
        ],
        tracking=True,
    )
    termination_effective_date = fields.Date(index=True, tracking=True)
    termination_reason = fields.Text(tracking=True)
    termination_review_state = fields.Selection(
        [("none", "Not Requested"), ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
        required=True, default="none", copy=False, tracking=True,
    )
    termination_reviewed_at = fields.Datetime(readonly=True, copy=False)
    terminated_at = fields.Datetime(readonly=True, copy=False)
    terminated_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    clearance_checklist_id = fields.Many2one(
        "onehr.checklist.instance", ondelete="restrict", copy=False, readonly=True,
    )
    clearance_task_ids = fields.One2many(
        related="clearance_checklist_id.task_ids", string="Clearance Tasks", readonly=True,
    )

    document_count = fields.Integer(
        compute="_compute_document_count", groups="onehr_employment_contract.group_onehr_contract_officer",
    )

    _STATE_CONTEXT = "onehr_contract_state_action"
    _EVIDENCE_CONTEXT = "onehr_contract_evidence_action"

    @api.model_create_multi
    def create(self, vals_list):
        require_contract_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            employee = self.env["hr.employee"].browse(vals.get("employee_id")).exists()
            version = self.env["hr.version"].browse(vals.get("hr_version_id")).exists()
            template = self.env["onehr.contract.template"].browse(vals.get("template_id")).exists()
            if not employee or not version or not template:
                raise ValidationError(_("Employee, Native HR Version and Contract Template are required."))
            vals.setdefault("company_id", employee.company_id.id)
            vals.setdefault("responsible_user_id", self.env.user.id)
            vals.setdefault("contract_kind", template.default_contract_kind)
            vals.setdefault("expiry_reminder_lead_days", template.expiry_reminder_lead_days)
            if vals.get("name") in (None, False, "", _("New")):
                vals["name"] = self.env["ir.sequence"].next_by_code("onehr.employment.contract") or _("New")
            prepared.append(vals)
        records = super().create(prepared)
        records._validate_contract_integrity()
        for record in records:
            self.env["onehr.audit.log"]._log_event(
                action="create",
                summary=_("Employment contract governance record created: %s", record.display_name),
                severity="high",
                record=record,
                company=record.company_id,
                after={"employee_id": record.employee_id.id, "hr_version_id": record.hr_version_id.id, "template_id": record.template_id.id},
            )
        return records

    def write(self, vals):
        values = dict(vals)
        if "state" in values and not self.env.context.get(self._STATE_CONTEXT):
            raise AccessError(_("Contract state can change only through governed business actions."))
        evidence_fields = {
            "snapshot_contract_start", "snapshot_contract_end", "snapshot_trial_end",
            "snapshot_contract_wage", "snapshot_currency_id", "snapshot_job_name",
            "snapshot_department_name", "snapshot_position_name", "snapshot_grade_name",
            "snapshot_engagement_type_name", "snapshot_template_code", "snapshot_template_version",
            "approved_at", "activated_at", "activated_by_id", "pending_approval_kind",
            "termination_review_state", "termination_reviewed_at",
            "terminated_at", "terminated_by_id", "clearance_checklist_id",
        }
        if evidence_fields & set(values) and not self.env.context.get(self._EVIDENCE_CONTEXT):
            raise AccessError(_("Frozen contract evidence can change only through governed business actions."))
        protected_identity = {"company_id", "employee_id", "hr_version_id", "template_id", "contract_kind", "predecessor_contract_id"}
        if protected_identity & set(values) and any(record.state != "draft" for record in self):
            raise AccessError(_("Submitted contract identity cannot be rewritten; create a successor contract instead."))
        result = super().write(values)
        if {"employee_id", "hr_version_id", "template_id", "company_id", "predecessor_contract_id"} & set(values):
            self._validate_contract_integrity()
        return result

    @api.constrains("employee_id", "hr_version_id", "template_id", "company_id", "predecessor_contract_id")
    def _check_contract_integrity(self):
        self._validate_contract_integrity()

    def _validate_contract_integrity(self):
        for record in self:
            if record.employee_id.company_id != record.company_id:
                raise ValidationError(_("Employee and contract must belong to the same company."))
            if record.hr_version_id.employee_id != record.employee_id:
                raise ValidationError(_("Native HR Version must belong to the selected employee."))
            if record.hr_version_id.company_id != record.company_id:
                raise ValidationError(_("Native HR Version and contract company must match."))
            if not record.hr_version_id.contract_date_start:
                raise ValidationError(_("Native HR Version must represent an Odoo contract interval with Contract Start."))
            if not record.template_id.matches_hr_version(record.hr_version_id, record.hr_version_id.contract_date_start):
                raise ValidationError(_("Contract Template is not active/effective/applicable for the selected Native HR Version."))
            if self.search_count([
                ("id", "!=", record.id), ("hr_version_id", "=", record.hr_version_id.id),
                ("state", "not in", ["rejected"]),
            ], limit=1):
                raise ValidationError(_("Only one non-rejected OneHR contract wrapper may govern the same Native HR Version."))
            if record.predecessor_contract_id:
                if record.predecessor_contract_id.employee_id != record.employee_id:
                    raise ValidationError(_("Successor and predecessor contracts must belong to the same employee."))
                if record.predecessor_contract_id == record:
                    raise ValidationError(_("A contract cannot be its own predecessor."))
                visited = set()
                cursor = record.predecessor_contract_id
                while cursor:
                    if cursor.id in visited or cursor == record:
                        raise ValidationError(_("Contract predecessor/successor history cannot contain a cycle."))
                    visited.add(cursor.id)
                    cursor = cursor.predecessor_contract_id
        return True

    @api.constrains("expiry_reminder_lead_days")
    def _check_reminder_days(self):
        if any(record.expiry_reminder_lead_days < 0 for record in self):
            raise ValidationError(_("Expiry reminder lead days cannot be negative."))

    @api.constrains("termination_effective_date", "termination_type", "termination_reason")
    def _check_termination_details(self):
        for record in self:
            if record.termination_effective_date:
                if record.native_contract_start and record.termination_effective_date < record.native_contract_start:
                    raise ValidationError(_("Termination date cannot be before Contract Start."))
                if record.native_contract_end and record.termination_effective_date > record.native_contract_end:
                    raise ValidationError(_("Termination date cannot be after the current Contract End."))

    @api.depends("successor_contract_ids")
    def _compute_successor_count(self):
        for record in self:
            record.successor_count = len(record.successor_contract_ids)

    def _compute_days_to_expiry(self):
        today = fields.Date.context_today(self)
        for record in self:
            record.days_to_expiry = (record.native_contract_end - today).days if record.native_contract_end else 0

    def _compute_document_count(self):
        try:
            Document = self.env["onehr.document"]
        except KeyError:
            for record in self:
                record.document_count = 0
            return
        for record in self:
            record.document_count = Document.search_count([
                ("source_model_id.model", "=", self._name),
                ("source_res_id", "=", record.id),
            ])

    def _snapshot_values(self):
        self.ensure_one()
        version = self.hr_version_id
        return {
            "snapshot_contract_start": version.contract_date_start,
            "snapshot_contract_end": version.contract_date_end,
            "snapshot_trial_end": version.trial_date_end,
            "snapshot_contract_wage": version.contract_wage,
            "snapshot_currency_id": self.company_id.currency_id.id,
            "snapshot_job_name": version.job_id.display_name if version.job_id else False,
            "snapshot_department_name": version.department_id.display_name if version.department_id else False,
            "snapshot_position_name": version.onehr_primary_position_id.display_name if version.onehr_primary_position_id else False,
            "snapshot_grade_name": version.onehr_grade_id.display_name if version.onehr_grade_id else False,
            "snapshot_engagement_type_name": version.onehr_engagement_type_id.display_name if version.onehr_engagement_type_id else False,
            "snapshot_template_code": self.template_id.code,
            "snapshot_template_version": self.template_id.version,
        }

    def _approval_payload(self):
        self.ensure_one()
        if self.pending_approval_kind == "termination":
            return {
                "purpose": "termination",
                "contract": self.name,
                "employee": self.employee_id.display_name,
                "termination_type": self.termination_type,
                "termination_effective_date": fields.Date.to_string(self.termination_effective_date) if self.termination_effective_date else False,
                "termination_reason": self.termination_reason,
            }
        snapshot = self._snapshot_values()
        return {
            "purpose": "contract",
            "contract": self.name,
            "employee": self.employee_id.display_name,
            "template": f"{self.template_id.code}/v{self.template_id.version}",
            "contract_start": fields.Date.to_string(snapshot["snapshot_contract_start"]),
            "contract_end": fields.Date.to_string(snapshot["snapshot_contract_end"]) if snapshot["snapshot_contract_end"] else False,
            "trial_end": fields.Date.to_string(snapshot["snapshot_trial_end"]) if snapshot["snapshot_trial_end"] else False,
            "wage": snapshot["snapshot_contract_wage"],
            "currency": self.company_id.currency_id.name,
        }

    def _approval_rule_context(self):
        self.ensure_one()
        values = super()._approval_rule_context()
        # Line-manager access is deliberately read-only. Approval rules should
        # route to users with Contract Manager authority, which includes the
        # workflow Approver role and source-record write rights.
        manager_ids = []
        purpose = "employment_contract_termination" if self.pending_approval_kind == "termination" else "employment_contract"
        values.update({
            "document_type": purpose,
            "amount": 0.0 if self.pending_approval_kind == "termination" else self.native_contract_wage,
            "currency_id": self.company_id.currency_id.id,
            "manager_user_ids": manager_ids,
            "extra": {
                "employee_id": self.employee_id.id,
                "hr_version_id": self.hr_version_id.id,
                "template_id": self.template_id.id,
                "contract_kind": self.contract_kind,
            },
        })
        return values

    def _has_pending_approval(self):
        self.ensure_one()
        return bool(self.env["onehr.approval.request"].search_count([
            ("source_model", "=", self._name), ("source_res_id", "=", self.id),
            ("state", "in", ["draft", "submitted", "pending"]),
        ], limit=1))

    def action_submit_for_review(self):
        self.ensure_one()
        require_contract_officer(self)
        if self.state != "draft":
            raise UserError(_("Only a draft contract may be submitted for review."))
        self._validate_contract_integrity()
        if self._has_pending_approval():
            raise UserError(_("This contract already has a pending approval request."))
        values = self._snapshot_values() | {"pending_approval_kind": "contract", "state": "in_review"}
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write(values)
        return super().action_submit_for_approval()

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        evidence_context = {self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}
        if self.pending_approval_kind == "termination":
            self.with_context(**evidence_context).write({
                "termination_review_state": "approved" if decision == "approve" else "rejected",
                "termination_reviewed_at": fields.Datetime.now(),
                "pending_approval_kind": False,
            })
            return True
        if self.state == "in_review":
            self.with_context(**evidence_context).write({
                "state": "approved" if decision == "approve" else "rejected",
                "approved_at": fields.Datetime.now() if decision == "approve" else False,
                "pending_approval_kind": False,
            })
        return True

    def action_reset_to_draft(self):
        self.ensure_one()
        require_contract_officer(self)
        if self.state != "rejected":
            raise UserError(_("Only a rejected contract can be reset to draft."))
        self.with_context(**{self._STATE_CONTEXT: True}).write({"state": "draft"})
        return True

    def _latest_approved_request(self):
        self.ensure_one()
        return self.env["onehr.approval.request"].search([
            ("source_model", "=", self._name), ("source_res_id", "=", self.id), ("state", "=", "approved")
        ], order="finalized_at desc, id desc", limit=1)

    def action_activate(self):
        self.ensure_one()
        require_contract_manager(self)
        if self.state != "approved":
            raise UserError(_("Only an approved contract can be activated."))
        if self.native_contract_start > fields.Date.context_today(self):
            raise UserError(_("A future-dated contract remains Approved until its Contract Start date."))
        request = self._latest_approved_request()
        if not request:
            raise UserError(_("Approved workflow evidence is required before activation."))
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "active", "activated_at": fields.Datetime.now(), "activated_by_id": self.env.user.id,
        })
        self.onehr_mark_approval_executed(request)
        self.env["onehr.audit.log"]._log_event(
            action="activate", summary=_("Employment contract activated: %s", self.display_name),
            severity="high", record=self, company=self.company_id,
            metadata={"hr_version_id": self.hr_version_id.id, "contract_start": self.native_contract_start},
        )
        self._onehr_after_contract_activation()
        return True

    def _onehr_after_contract_activation(self):
        """Downstream payroll/work-entry owners may extend without reverse dependency."""
        self.ensure_one()
        return True

    def action_create_renewal(self):
        self.ensure_one()
        require_contract_manager(self)
        if self.state not in {"active", "expired"}:
            raise UserError(_("A renewal can be prepared only from an Active or Expired contract."))
        if not self.native_contract_end:
            raise UserError(_("Set the canonical Odoo Contract End before creating a renewal."))
        next_start = self.native_contract_end + timedelta(days=1)
        new_version = self.employee_id.create_contract(next_start)[:1]
        template = self.template_id
        if not template.matches_hr_version(new_version, next_start):
            template = self.env["onehr.contract.template"].search([
                ("code", "=ilike", self.template_id.code), ("state", "=", "active"),
                ("valid_from", "<=", next_start), "|", ("valid_to", "=", False), ("valid_to", ">=", next_start),
                "|", ("company_id", "=", False), ("company_id", "=", self.company_id.id),
            ], order="company_id desc, version desc, id desc", limit=1)
        if not template or not template.matches_hr_version(new_version, next_start):
            raise UserError(_("No active applicable contract-template version is available for the renewal start date."))
        renewal = self.create({
            "employee_id": self.employee_id.id,
            "company_id": self.company_id.id,
            "hr_version_id": new_version.id,
            "template_id": template.id,
            "contract_kind": "renewal",
            "predecessor_contract_id": self.id,
            "responsible_user_id": self.responsible_user_id.id,
        })
        return open_record_action(name=_("Renewal Contract"), res_model=self._name, res_id=renewal.id)

    def action_request_termination_review(self):
        self.ensure_one()
        require_contract_manager(self)
        if self.state != "active":
            raise UserError(_("Termination approval may be requested only for an Active contract."))
        if not self.termination_type or not self.termination_effective_date or not self.termination_reason:
            raise UserError(_("Termination Type, Effective Date and Reason are required."))
        self._check_termination_details()
        if self._has_pending_approval():
            raise UserError(_("This contract already has a pending approval request."))
        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write({
            "pending_approval_kind": "termination", "termination_review_state": "pending",
        })
        return super().action_submit_for_approval()

    def _find_termination_checklist_template(self):
        self.ensure_one()
        event_type = self.env["onehr.lifecycle.event.type"].search([("code", "=", "TERMINATION")], limit=1)
        if not event_type:
            raise UserError(_("OneHR lifecycle event type TERMINATION is missing."))
        date = self.termination_effective_date
        template = self.env["onehr.checklist.template"].search([
            ("lifecycle_event_type_id", "=", event_type.id), ("state", "=", "active"),
            ("valid_from", "<=", date), "|", ("valid_to", "=", False), ("valid_to", ">=", date),
            "|", ("company_id", "=", False), ("company_id", "=", self.company_id.id),
        ], order="company_id desc, version desc, id desc", limit=1)
        if not template:
            raise UserError(_("Configure an active TERMINATION clearance checklist before executing termination."))
        return template

    def action_execute_termination(self):
        self.ensure_one()
        require_contract_manager(self)
        if self.state != "active" or self.termination_review_state != "approved":
            raise UserError(_("An Active contract with approved termination review is required."))
        self._check_termination_details()
        checklist_template = self._find_termination_checklist_template()

        # Odoo 19 groups contract versions by employee + contract_date_start.
        # Update every version row in that native contract interval using normal
        # ORM rights so canonical Odoo facts remain coherent without sudo bypass.
        contract_versions = self.env["hr.version"].search([
            ("employee_id", "=", self.employee_id.id),
            ("contract_date_start", "=", self.hr_version_id.contract_date_start),
        ])
        contract_versions.write({"contract_date_end": self.termination_effective_date})

        checklist = self.clearance_checklist_id
        if not checklist:
            checklist = self.env["onehr.checklist.instance"].create({
                "employee_id": self.employee_id.id,
                "company_id": self.company_id.id,
                "template_id": checklist_template.id,
                "event_date": self.termination_effective_date,
                "source_model": self._name,
                "source_res_id": self.id,
            })
        self.with_context(**{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}).write({
            "state": "terminated",
            "terminated_at": fields.Datetime.now(),
            "terminated_by_id": self.env.user.id,
            "clearance_checklist_id": checklist.id,
        })
        request = self._latest_approved_request()
        if request:
            self.onehr_mark_approval_executed(request)
        self.env["onehr.audit.log"]._log_event(
            action="other", summary=_("Employment contract terminated: %s", self.display_name),
            severity="critical", record=self, company=self.company_id,
            metadata={
                "termination_type": self.termination_type,
                "termination_effective_date": self.termination_effective_date,
                "clearance_checklist_id": checklist.id,
            },
        )
        self._onehr_after_contract_termination()
        return self.action_open_clearance_checklist()

    def _onehr_after_contract_termination(self):
        """Offboarding/payroll owners may extend; this addon does not archive the employee."""
        self.ensure_one()
        return True

    def action_schedule_expiry_reminder(self):
        self.ensure_one()
        require_contract_officer(self)
        if self.state not in {"approved", "active"} or not self.native_contract_end:
            raise UserError(_("Expiry reminders require an Approved/Active fixed-end contract."))
        if self.expiry_reminder_sent_at:
            return True
        deadline = max(fields.Date.context_today(self), self.native_contract_end - timedelta(days=self.expiry_reminder_lead_days))
        self.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=self.responsible_user_id.id,
            date_deadline=deadline,
            summary=_("Contract expiry review — %s", self.employee_id.display_name),
        )
        self.with_context(**{self._EVIDENCE_CONTEXT: True}).write({"expiry_reminder_sent_at": fields.Datetime.now()})
        return True

    @api.model
    def cron_manage_contract_lifecycle(self):
        today = fields.Date.context_today(self)
        candidates = self.search([
            ("state", "in", ["approved", "active"]),
            ("hr_version_id.contract_date_end", "!=", False),
        ])
        for record in candidates:
            end = record.native_contract_end
            if record.state in {"approved", "active"} and end and end < today:
                record.with_context(**{record._STATE_CONTEXT: True}).write({"state": "expired"})
                continue
            if end and not record.expiry_reminder_sent_at and end <= today + timedelta(days=record.expiry_reminder_lead_days):
                # Cron is a mechanical follow-up after business configuration;
                # the normal activity API and record rules remain in force.
                deadline = max(today, end - timedelta(days=record.expiry_reminder_lead_days))
                record.activity_schedule(
                    "mail.mail_activity_data_todo", user_id=record.responsible_user_id.id,
                    date_deadline=deadline, summary=_("Contract expiry review — %s", record.employee_id.display_name),
                )
                record.with_context(**{record._EVIDENCE_CONTEXT: True}).write({"expiry_reminder_sent_at": fields.Datetime.now()})
        return True

    def action_generate_contract_document(self):
        """Soft onehr_document integration; no hard dependency or source edit."""
        self.ensure_one()
        require_contract_officer(self)
        if self.state not in {"approved", "active", "expired", "terminated"}:
            raise UserError(_("Generate a governed contract document only after contract approval."))
        try:
            DocumentTemplate = self.env["onehr.document.template"]
            self.env["wizard.document.generate"]
        except KeyError as exc:
            raise UserError(_("OneHR Document is not installed. Install it to generate governed contract documents.")) from exc
        code = (self.template_id.document_template_code or "EMPLOYMENT_CONTRACT").strip()
        template = DocumentTemplate.search([
            ("code", "=ilike", code), ("active", "=", True),
            "|", ("company_id", "=", False), ("company_id", "=", self.company_id.id),
        ], order="company_id desc, id desc", limit=1)
        if not template:
            raise UserError(_("Create an active OneHR Document template with code %s first.", code))
        source_model = self.env["ir.model"]._get(self._name)
        return {
            "type": "ir.actions.act_window",
            "name": _("Generate Contract Document"),
            "res_model": "wizard.document.generate",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_template_id": template.id,
                "default_company_id": self.company_id.id,
                "default_employee_id": self.employee_id.id,
                "default_category_id": template.category_id.id,
                "default_source_model_id": source_model.id,
                "default_source_res_id": self.id,
                "default_document_name": _("Employment Contract — %s", self.employee_id.display_name),
                "default_effective_from": self.snapshot_contract_start or self.native_contract_start,
                "default_effective_to": self.snapshot_contract_end or self.native_contract_end,
                "default_expiry_date": self.snapshot_contract_end or self.native_contract_end,
            },
        }

    def _require_document_manager_if_installed(self):
        """Validate soft-integration authority without creating a hard dependency."""
        self.ensure_one()
        group = self.env.ref(
            "onehr_document.group_onehr_document_manager",
            raise_if_not_found=False,
        )
        if group and not self.env.user.has_group(
            "onehr_document.group_onehr_document_manager"
        ):
            raise AccessError(
                _("Document Manager authority is required to request an e-signature.")
            )
        return True

    def action_request_contract_signature(self):
        """Open OneHR Document's governed e-sign workflow for the latest contract document."""
        self.ensure_one()
        require_contract_officer(self)
        try:
            Document = self.env["onehr.document"]
            self.env["wizard.document.publish.sign"]
        except KeyError as exc:
            raise UserError(
                _("OneHR Document is not installed. Install it to use the governed e-signature workflow.")
            ) from exc

        self._require_document_manager_if_installed()
        document = Document.search(
            [
                ("source_model_id.model", "=", self._name),
                ("source_res_id", "=", self.id),
            ],
            order="id desc",
            limit=1,
        )
        if not document:
            raise UserError(
                _("Generate a governed contract document before requesting an e-signature.")
            )
        if not document.current_version_id:
            raise UserError(_("The contract document has no current document version."))
        return document.current_version_id.action_request_signature()

    def action_open_documents(self):
        self.ensure_one()
        require_contract_officer(self)
        try:
            self.env["onehr.document"]
        except KeyError as exc:
            raise UserError(_("OneHR Document is not installed.")) from exc
        return open_records_action(
            name=_("Contract Documents — %s", self.name), res_model="onehr.document",
            domain=[("source_model_id.model", "=", self._name), ("source_res_id", "=", self.id)],
        )

    def action_open_employee(self):
        """Open the private HR employee only for Contract Officers.

        Line managers are intentionally read-only contract viewers and do not
        receive private ``hr.employee`` ACLs. They are routed to the native
        employee directory model instead.
        """
        self.ensure_one()
        if self.env.user.has_group("onehr_employment_contract.group_onehr_contract_officer"):
            return open_record_action(
                name=_("Employee"),
                res_model="hr.employee",
                res_id=self.employee_id.id,
            )
        return open_record_action(
            name=_("Employee Directory"),
            res_model="hr.employee.public",
            res_id=self.employee_id.id,
        )

    def action_open_hr_version(self):
        self.ensure_one()
        require_contract_officer(self)
        return open_record_action(name=_("Native HR Version"), res_model="hr.version", res_id=self.hr_version_id.id)

    def action_open_successors(self):
        self.ensure_one()
        return open_records_action(
            name=_("Successor Contracts — %s", self.name), res_model=self._name,
            domain=[("predecessor_contract_id", "=", self.id)],
            context={"default_predecessor_contract_id": self.id, "default_employee_id": self.employee_id.id},
        )

    def action_open_clearance_checklist(self):
        self.ensure_one()
        require_contract_officer(self)
        if not self.clearance_checklist_id:
            raise UserError(_("No termination clearance checklist has been allocated."))
        return open_record_action(
            name=_("Termination Clearance"), res_model="onehr.checklist.instance", res_id=self.clearance_checklist_id.id,
        )

    def action_schedule_clearance_activities(self):
        self.ensure_one()
        require_contract_officer(self)
        if not self.clearance_checklist_id:
            raise UserError(_("No termination clearance checklist has been allocated."))
        self.clearance_checklist_id.action_schedule_outstanding_activities()
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_except_module_uninstall(self):
        if any(record.state != "draft" or record.onehr_approval_request_count for record in self):
            raise AccessError(_("Only untouched draft contracts without approval evidence may be deleted."))

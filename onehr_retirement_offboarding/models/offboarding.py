from collections import Counter
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action, open_records_action
from .security_helpers import (
    require_offboarding_admin,
    require_offboarding_manager,
    require_offboarding_officer,
    require_system_admin,
)


class OneHROffboarding(models.Model):
    """Enterprise exit-orchestration case.

    This model coordinates clearance and exit evidence. It intentionally does not
    own canonical employee facts, legal contract termination, payroll calculation,
    document generation, portal transport, API transport or branch masters.
    """

    _name = "onehr.offboarding"
    _description = "OneHR Retirement & Offboarding Case"
    _inherit = ["onehr.mixin.audit", "onehr.mixin.approvable"]
    _order = "request_date desc, id desc"

    name = fields.Char(default=lambda self: _("New"), readonly=True, copy=False, index=True)
    employee_id = fields.Many2one(
        "hr.employee", required=True, ondelete="restrict", index=True, tracking=True
    )
    company_id = fields.Many2one(
        "res.company", required=True, ondelete="restrict", index=True, tracking=True,
        default=lambda self: self.env.company,
    )
    employee_number = fields.Char(readonly=True, copy=False, groups="onehr_retirement_offboarding.group_onehr_offboarding_officer")
    department_id = fields.Many2one("hr.department", readonly=True, copy=False, index=True)
    job_id = fields.Many2one("hr.job", readonly=True, copy=False, index=True)
    manager_employee_id = fields.Many2one("hr.employee", readonly=True, copy=False)
    responsible_user_id = fields.Many2one(
        "res.users", required=True, ondelete="restrict", tracking=True,
        default=lambda self: self.env.user,
    )
    branch_scope_key = fields.Char(
        tracking=True,
        help="Soft branch routing key. Branch master ownership remains outside this addon.",
    )

    offboarding_type = fields.Selection(
        [
            ("resignation", "Resignation"),
            ("retirement", "Retirement"),
            ("employer_termination", "Employer Termination"),
            ("mutual", "Mutual Agreement"),
            ("other", "Other"),
        ],
        required=True,
        default="resignation",
        index=True,
        tracking=True,
    )
    request_date = fields.Date(required=True, default=fields.Date.context_today, index=True, tracking=True)
    proposed_exit_date = fields.Date(required=True, index=True, tracking=True)
    approved_exit_date = fields.Date(readonly=True, copy=False, index=True)
    effective_exit_date = fields.Date(readonly=True, copy=False, index=True)
    target_close_date = fields.Date(readonly=True, copy=False, index=True)
    exit_reason_code = fields.Selection(
        [
            ("career", "Career Opportunity"),
            ("compensation", "Compensation / Benefits"),
            ("manager", "Manager / Leadership"),
            ("culture", "Culture / Environment"),
            ("relocation", "Relocation / Family"),
            ("retirement", "Retirement"),
            ("health", "Personal / Health"),
            ("performance", "Performance / Employer Decision"),
            ("mutual", "Mutual Agreement"),
            ("other", "Other"),
        ],
        tracking=True,
        index=True,
    )
    exit_reason_notes = fields.Text(
        tracking=True,
        groups="onehr_retirement_offboarding.group_onehr_offboarding_officer",
    )
    state = fields.Selection(
        [
            ("requested", "Requested"),
            ("approval", "Approval"),
            ("in_progress", "In Progress"),
            ("completed", "Completed"),
            ("closed", "Closed"),
            ("rejected", "Rejected"),
            ("cancelled", "Cancelled"),
        ],
        default="requested",
        required=True,
        index=True,
        tracking=True,
    )
    last_approval_request_id = fields.Many2one("onehr.approval.request", readonly=True, copy=False)
    approval_finalized_at = fields.Datetime(readonly=True, copy=False)

    checklist_ids = fields.One2many("onehr.offboarding.checklist", "offboarding_id", string="Clearance Tasks")
    checklist_count = fields.Integer(compute="_compute_operational_summary")
    mandatory_open_count = fields.Integer(compute="_compute_operational_summary")
    overdue_task_count = fields.Integer(compute="_compute_operational_summary")
    completion_percent = fields.Float(compute="_compute_operational_summary")
    exit_interview_ids = fields.One2many("onehr.exit.interview", "offboarding_id", string="Exit Interview")
    exit_interview_count = fields.Integer(compute="_compute_operational_summary")

    access_state = fields.Selection(
        [
            ("pending", "Pending"),
            ("requested", "Revoke Requested"),
            ("revoked", "Odoo Revoked"),
            ("external_confirmed", "External/SSO Confirmed"),
            ("not_required", "Not Required"),
        ],
        default="pending",
        required=True,
        tracking=True,
    )
    access_requested_at = fields.Datetime(readonly=True, copy=False)
    access_revoked_at = fields.Datetime(readonly=True, copy=False)
    access_revoked_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    access_external_reference = fields.Char(copy=False, tracking=True)
    access_note = fields.Text(
        groups="onehr_retirement_offboarding.group_onehr_offboarding_admin",
        tracking=True,
    )

    final_benefit_state = fields.Selection(
        [
            ("not_requested", "Not Requested"),
            ("requested", "Requested"),
            ("confirmed", "Confirmed"),
            ("not_required", "Not Required"),
        ],
        default="not_requested",
        required=True,
        tracking=True,
    )
    final_benefit_reference = fields.Char(
        groups="onehr_retirement_offboarding.group_onehr_offboarding_manager",
        tracking=True,
    )
    final_benefit_amount = fields.Monetary(
        currency_field="currency_id",
        groups="onehr_retirement_offboarding.group_onehr_offboarding_manager",
        tracking=True,
    )
    final_benefit_note = fields.Text(
        groups="onehr_retirement_offboarding.group_onehr_offboarding_manager",
        tracking=True,
    )
    currency_id = fields.Many2one(related="company_id.currency_id", store=True)

    contract_res_id = fields.Integer(readonly=True, copy=False)
    contract_reference = fields.Char(readonly=True, copy=False)
    contract_termination_state = fields.Selection(
        [
            ("not_checked", "Not Checked"),
            ("not_installed", "Employment Contract Not Installed"),
            ("not_started", "Not Started"),
            ("pending", "Termination Approval Pending"),
            ("approved", "Termination Approved"),
            ("rejected", "Termination Rejected"),
            ("terminated", "Terminated"),
            ("not_applicable", "Not Applicable"),
        ],
        default="not_checked",
        required=True,
        tracking=True,
    )
    contract_exception_note = fields.Text(tracking=True)
    document_reference = fields.Char(tracking=True)

    readiness_state = fields.Selection(
        [("not_ready", "Not Ready"), ("ready", "Ready")],
        compute="_compute_readiness_state",
        store=False,
    )
    completed_at = fields.Datetime(readonly=True, copy=False)
    completed_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    closed_at = fields.Datetime(readonly=True, copy=False)
    closed_by_id = fields.Many2one("res.users", readonly=True, copy=False)
    cycle_days = fields.Integer(readonly=True, copy=False, help="Calendar days from request to effective exit, frozen at closure.")

    _CASE_STATE_CONTEXT = "onehr_offboarding_state_action"
    _CASE_EVIDENCE_CONTEXT = "onehr_offboarding_evidence_action"

    @api.model_create_multi
    def create(self, vals_list):
        require_offboarding_officer(self)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            employee = self.env["hr.employee"].browse(vals.get("employee_id")).exists()
            if not employee:
                raise ValidationError(_("A valid Employee is required."))
            company = employee.company_id or self.env.company
            vals["company_id"] = company.id
            vals.setdefault("responsible_user_id", self.env.user.id)
            vals.setdefault("request_date", fields.Date.context_today(self))
            vals["employee_number"] = getattr(employee, "employee_number", False) or getattr(employee, "identification_id", False) or False
            vals["department_id"] = employee.department_id.id if employee.department_id else False
            vals["job_id"] = employee.job_id.id if employee.job_id else False
            vals["manager_employee_id"] = employee.parent_id.id if employee.parent_id else False
            if vals.get("name") in (None, False, "", _("New")):
                vals["name"] = self.env["ir.sequence"].next_by_code("onehr.offboarding") or _("New")
            prepared.append(vals)
        records = super().create(prepared)
        records._check_open_case_uniqueness()
        return records

    def write(self, vals):
        values = dict(vals)
        if "state" in values and not self.env.context.get(self._CASE_STATE_CONTEXT):
            raise ValidationError(_("Use governed Offboarding workflow actions to change Case State."))
        evidence_fields = {
            "approved_exit_date", "effective_exit_date", "target_close_date",
            "last_approval_request_id", "approval_finalized_at",
            "access_state", "access_requested_at", "access_revoked_at", "access_revoked_by_id",
            "final_benefit_state", "contract_res_id", "contract_reference", "contract_termination_state",
            "completed_at", "completed_by_id", "closed_at", "closed_by_id", "cycle_days",
        }
        if evidence_fields.intersection(values) and not self.env.context.get(self._CASE_EVIDENCE_CONTEXT):
            raise ValidationError(_("Governed offboarding evidence fields may be changed only by their business actions."))
        snapshot_fields = {"employee_id", "company_id", "employee_number", "department_id", "job_id", "manager_employee_id"}
        if snapshot_fields.intersection(values) and self.filtered(lambda r: r.state not in ("requested", "rejected")):
            raise ValidationError(_("Employee and organization snapshots cannot change after approval starts."))
        if self.filtered(lambda r: r.state == "closed") and not self.env.context.get(self._CASE_EVIDENCE_CONTEXT):
            mutable_after_close = {"message_follower_ids", "message_partner_ids"}
            if set(values) - mutable_after_close:
                raise ValidationError(_("Closed offboarding evidence is immutable."))
        result = super().write(values)
        if {"employee_id", "company_id", "state"}.intersection(values):
            self._check_open_case_uniqueness()
        return result

    def unlink(self):
        require_offboarding_admin(self)
        if self.filtered(lambda r: r.state not in ("requested", "rejected", "cancelled")):
            raise ValidationError(_("Started/completed offboarding cases cannot be deleted; retain their audit evidence."))
        return super().unlink()

    @api.constrains("employee_id", "company_id", "state")
    def _check_open_case_uniqueness(self):
        terminal = ("closed", "cancelled", "rejected")
        for record in self.filtered(lambda r: r.state not in terminal):
            if self.search_count(
                [
                    ("id", "!=", record.id),
                    ("employee_id", "=", record.employee_id.id),
                    ("company_id", "=", record.company_id.id),
                    ("state", "not in", terminal),
                ],
                limit=1,
            ):
                raise ValidationError(_("Only one open offboarding case is allowed per employee and company."))

    @api.constrains("proposed_exit_date", "request_date")
    def _check_exit_dates(self):
        for record in self:
            if record.proposed_exit_date and record.request_date and record.proposed_exit_date < record.request_date:
                raise ValidationError(_("Proposed Exit Date cannot be before Request Date."))

    @api.depends("checklist_ids.state", "checklist_ids.due_date", "checklist_ids.mandatory", "exit_interview_ids.state")
    def _compute_operational_summary(self):
        today = fields.Date.context_today(self)
        for record in self:
            tasks = record.checklist_ids
            record.checklist_count = len(tasks)
            record.mandatory_open_count = len(tasks.filtered(lambda t: t.mandatory and t.state not in ("done", "waived")))
            record.overdue_task_count = len(tasks.filtered(lambda t: t.due_date and t.due_date < today and t.state not in ("done", "waived")))
            record.completion_percent = round((len(tasks.filtered(lambda t: t.state in ("done", "waived"))) / len(tasks) * 100.0), 2) if tasks else 0.0
            record.exit_interview_count = len(record.exit_interview_ids)

    @api.depends("checklist_ids.state", "checklist_ids.mandatory", "exit_interview_ids.state", "access_state", "final_benefit_state", "contract_termination_state")
    def _compute_readiness_state(self):
        for record in self:
            record.readiness_state = "ready" if not record._readiness_blockers() else "not_ready"

    def _readiness_blockers(self):
        self.ensure_one()
        blockers = []
        if not self.checklist_ids:
            blockers.append(_("no clearance checklist has been generated"))
        if self.checklist_ids.filtered(lambda t: t.mandatory and t.state not in ("done", "waived")):
            blockers.append(_("mandatory clearance tasks remain open"))
        interview = self.exit_interview_ids[:1]
        if not interview or interview.state not in ("submitted", "waived"):
            blockers.append(_("exit interview is not submitted or waived"))
        if self.access_state not in ("revoked", "external_confirmed", "not_required"):
            blockers.append(_("access revocation is not completed or marked not required"))
        if self.final_benefit_state not in ("confirmed", "not_required"):
            blockers.append(_("final benefit disposition is not confirmed or marked not required"))
        if self.contract_termination_state not in ("terminated", "not_applicable"):
            blockers.append(_("legal employment-contract termination is not completed or marked not applicable"))
        return blockers

    # ------------------------------------------------------------------
    # Workflow Approval integration — source retains business state.
    # ------------------------------------------------------------------
    def _approval_payload(self):
        self.ensure_one()
        return {
            "offboarding_reference": self.name,
            "employee_id": self.employee_id.id,
            "employee_name": self.employee_id.name,
            "company_id": self.company_id.id,
            "offboarding_type": self.offboarding_type,
            "proposed_exit_date": str(self.proposed_exit_date or ""),
            "exit_reason_code": self.exit_reason_code,
            "responsible_user_id": self.responsible_user_id.id,
        }

    def _approval_branch_scope_key(self):
        self.ensure_one()
        return self.branch_scope_key or False

    def _approval_rule_context(self):
        self.ensure_one()
        context = super()._approval_rule_context()
        manager_users = self.manager_employee_id.user_id.ids if self.manager_employee_id and self.manager_employee_id.user_id else []
        context.update(
            {
                "company_id": self.company_id.id,
                "branch_scope_key": self._approval_branch_scope_key(),
                "document_type": f"onehr.offboarding.{self.offboarding_type}",
                "risk_level": "high" if self.offboarding_type == "employer_termination" else "normal",
                "manager_user_ids": manager_users,
                "extra": {
                    "employee_id": self.employee_id.id,
                    "proposed_exit_date": str(self.proposed_exit_date or ""),
                },
            }
        )
        return context

    def _approval_cancel_guard(self, request):
        self.ensure_one()
        return self.state in ("approval", "rejected", "requested")

    def _on_approval_finalized(self, decision, request):
        self.ensure_one()
        if self.state != "approval":
            raise UserError(_("Offboarding approval finalized while the case is not in Approval state."))
        now = fields.Datetime.now()
        if decision == "approve":
            self.with_context(**{self._CASE_STATE_CONTEXT: True, self._CASE_EVIDENCE_CONTEXT: True}).write(
                {
                    "state": "in_progress",
                    "approved_exit_date": self.proposed_exit_date,
                    "target_close_date": self.proposed_exit_date + timedelta(days=7),
                    "last_approval_request_id": request.id,
                    "approval_finalized_at": now,
                }
            )
            self._generate_checklist_internal()
            self.onehr_mark_approval_executed(request)
        elif decision == "reject":
            self.with_context(**{self._CASE_STATE_CONTEXT: True, self._CASE_EVIDENCE_CONTEXT: True}).write(
                {"state": "rejected", "last_approval_request_id": request.id, "approval_finalized_at": now}
            )
        else:
            raise ValidationError(_("Unsupported offboarding approval decision."))
        return True

    def action_submit_offboarding_approval(self):
        require_offboarding_manager(self)
        self.ensure_one()
        if self.state not in ("requested", "rejected"):
            raise UserError(_("Only Requested or Rejected cases may be submitted for approval."))
        if not self.proposed_exit_date or not self.offboarding_type:
            raise UserError(_("Exit Type and Proposed Exit Date are required."))
        if not self._matching_clearance_items():
            raise UserError(_("No active clearance catalogue items apply to this employee and exit type."))
        active_request = self.env["onehr.approval.request"].search(
            [
                ("source_model", "=", self._name),
                ("source_res_id", "=", self.id),
                ("state", "in", ["draft", "submitted", "pending"]),
            ],
            limit=1,
        )
        if active_request:
            raise UserError(_("An active Workflow Approval request already exists for this case."))
        self.with_context(**{self._CASE_STATE_CONTEXT: True}).write({"state": "approval"})
        return self.action_submit_for_approval()

    # ------------------------------------------------------------------
    # Clearance orchestration
    # ------------------------------------------------------------------
    def _employee_current_grade(self):
        self.ensure_one()
        version = getattr(self.employee_id, "current_version_id", False)
        return getattr(version, "onehr_grade_id", False) if version else False

    def _matching_clearance_items(self):
        self.ensure_one()
        domain = [
            ("active", "=", True),
            "|", ("company_id", "=", False), ("company_id", "=", self.company_id.id),
            "|", ("job_id", "=", False), ("job_id", "=", self.job_id.id if self.job_id else False),
            "|", ("offboarding_type", "=", "all"), ("offboarding_type", "=", self.offboarding_type),
        ]
        grade = self._employee_current_grade()
        items = self.env["onehr.clearance.item"].search(domain, order="sequence, id")
        return items.filtered(lambda i: not i.grade_id or (grade and i.grade_id == grade))

    def _default_assignee_for_item(self, item):
        self.ensure_one()
        if item.owner_role == "hr":
            return self.responsible_user_id
        if item.owner_role == "manager" and self.manager_employee_id:
            return self.manager_employee_id.user_id
        if item.owner_role == "employee":
            return self.employee_id.user_id
        return self.env["res.users"]

    def action_generate_checklist(self):
        require_offboarding_manager(self)
        self.ensure_one()
        return self._generate_checklist_internal()

    def _generate_checklist_internal(self):
        self.ensure_one()
        if self.state not in ("in_progress", "approval"):
            raise UserError(_("Clearance checklist may be generated only during Approval/In Progress."))
        items = self._matching_clearance_items()
        if not items:
            raise UserError(_("No applicable active clearance items were found."))
        existing_ids = set(self.checklist_ids.clearance_item_id.ids)
        values = []
        base_date = self.approved_exit_date or self.proposed_exit_date
        for item in items.filtered(lambda i: i.id not in existing_ids):
            assignee = self._default_assignee_for_item(item)
            return_status = "pending" if item.category == "asset" else "not_applicable"
            values.append(
                {
                    "offboarding_id": self.id,
                    "clearance_item_id": item.id,
                    "sequence": item.sequence,
                    "item_code": item.code,
                    "title": item.name,
                    "category": item.category,
                    "owner_role": item.owner_role,
                    "mandatory": item.mandatory,
                    "instructions": item.instructions,
                    "assigned_user_id": assignee.id if assignee else False,
                    "due_date": base_date - timedelta(days=item.sla_days) if base_date else False,
                    "return_status": return_status,
                }
            )
        if values:
            self.env["onehr.offboarding.checklist"].with_context(onehr_offboarding_generate_tasks=True).create(values)
        return display_notification(
            _("%s clearance task(s) generated; %s already existed.") % (len(values), len(existing_ids)),
            notification_type="success",
        )

    def action_create_exit_interview(self):
        require_offboarding_officer(self)
        self.ensure_one()
        if self.exit_interview_ids:
            return open_record_action(
                name=_("Exit Interview"),
                res_model="onehr.exit.interview",
                res_id=self.exit_interview_ids[:1].id,
            )
        interview = self.env["onehr.exit.interview"].create(
            {
                "offboarding_id": self.id,
                "interviewer_user_id": self.responsible_user_id.id,
                "scheduled_at": fields.Datetime.now(),
                "primary_exit_reason": self.exit_reason_code or ("retirement" if self.offboarding_type == "retirement" else False),
            }
        )
        return open_record_action(name=_("Exit Interview"), res_model=interview._name, res_id=interview.id)

    def action_check_readiness(self):
        self.ensure_one()
        blockers = self._readiness_blockers()
        if blockers:
            return display_notification(
                _("Not ready to complete: %s") % "; ".join(blockers),
                notification_type="warning",
                sticky=True,
            )
        return display_notification(_("All closure gates are satisfied."), notification_type="success")

    # ------------------------------------------------------------------
    # Access revocation — explicit dual authority for native user disable.
    # ------------------------------------------------------------------
    def action_request_access_revoke(self):
        require_offboarding_manager(self)
        for record in self:
            if record.state != "in_progress":
                raise UserError(_("Access revocation may be requested only for an In Progress case."))
            record.with_context(**{record._CASE_EVIDENCE_CONTEXT: True}).write(
                {"access_state": "requested", "access_requested_at": fields.Datetime.now()}
            )
        return True

    def onehr_offboarding_access_revoke_payload(self):
        """Payload for Integration API/SSO adapter; no transport is owned here."""
        self.ensure_one()
        self.check_access("read")
        user = self.employee_id.user_id
        return {
            "reference": self.name,
            "employee_id": self.employee_id.id,
            "employee_name": self.employee_id.name,
            "user_id": user.id if user else False,
            "user_login": user.login if user else False,
            "effective_exit_date": str(self.approved_exit_date or self.proposed_exit_date or ""),
            "branch_scope_key": self.branch_scope_key or False,
        }

    def action_revoke_odoo_access(self):
        require_offboarding_admin(self)
        require_system_admin(self)
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError(_("Odoo access can be revoked only for an In Progress case."))
        user = self.employee_id.user_id
        if not user:
            raise UserError(_("The employee has no linked Odoo user. Use Not Required or external confirmation as appropriate."))
        if user == self.env.user:
            raise UserError(_("You cannot revoke your own Odoo access from an offboarding case."))
        now = fields.Datetime.now()
        user.with_context(onehr_offboarding_access_evidence=True).write(
            {
                "active": False,
                "onehr_offboarding_access_revoked": True,
                "onehr_offboarding_access_revoked_at": now,
                "onehr_offboarding_access_reference": self.name,
                "onehr_offboarding_access_revoked_by_id": self.env.user.id,
            }
        )
        self.with_context(**{self._CASE_EVIDENCE_CONTEXT: True}).write(
            {"access_state": "revoked", "access_revoked_at": now, "access_revoked_by_id": self.env.user.id}
        )
        return True

    def action_confirm_external_access_revoked(self):
        require_offboarding_manager(self)
        for record in self:
            if not record.access_external_reference:
                raise UserError(_("Enter an External Access Reference before confirming external/SSO revocation."))
            record.with_context(**{record._CASE_EVIDENCE_CONTEXT: True}).write(
                {"access_state": "external_confirmed", "access_revoked_at": fields.Datetime.now(), "access_revoked_by_id": self.env.user.id}
            )
        return True

    def action_mark_access_not_required(self):
        require_offboarding_manager(self)
        self.with_context(**{self._CASE_EVIDENCE_CONTEXT: True}).write({"access_state": "not_required"})
        return True

    # ------------------------------------------------------------------
    # Final benefit bridge — orchestration only, never payroll calculation.
    # ------------------------------------------------------------------
    def action_request_final_benefit(self):
        require_offboarding_manager(self)
        for record in self:
            record.with_context(**{record._CASE_EVIDENCE_CONTEXT: True}).write({"final_benefit_state": "requested"})
        return True

    def onehr_offboarding_payroll_payload(self):
        self.ensure_one()
        self.check_access("read")
        return {
            "reference": self.name,
            "employee_id": self.employee_id.id,
            "company_id": self.company_id.id,
            "offboarding_type": self.offboarding_type,
            "effective_exit_date": str(self.approved_exit_date or self.proposed_exit_date or ""),
            "calculate_amount": False,
        }

    def onehr_record_final_benefit_result(self, *, reference, amount=0.0, note=None):
        require_offboarding_manager(self)
        self.ensure_one()
        if not reference:
            raise ValidationError(_("Final-benefit result requires a source reference."))
        self.with_context(**{self._CASE_EVIDENCE_CONTEXT: True}).write(
            {
                "final_benefit_state": "confirmed",
                "final_benefit_reference": reference,
                "final_benefit_amount": amount or 0.0,
                "final_benefit_note": note or False,
            }
        )
        return True

    def action_mark_final_benefit_not_required(self):
        require_offboarding_manager(self)
        self.with_context(**{self._CASE_EVIDENCE_CONTEXT: True}).write({"final_benefit_state": "not_required"})
        return True

    # ------------------------------------------------------------------
    # Employment Contract — soft service boundary, ordinary ACL only.
    # ------------------------------------------------------------------
    def _employment_contract_model(self):
        return "onehr.contract" if self.env.registry.get("onehr.contract") else False

    def _resolve_employment_contract(self):
        self.ensure_one()
        model_name = self._employment_contract_model()
        if not model_name:
            return False
        Contract = self.env[model_name]
        if self.contract_res_id:
            contract = Contract.browse(self.contract_res_id).exists()
            if contract:
                return contract
        return Contract.search(
            [("employee_id", "=", self.employee_id.id), ("company_id", "=", self.company_id.id)],
            order="id desc",
            limit=1,
        )

    def _map_contract_termination_type(self):
        return {
            "resignation": "resignation",
            "retirement": "retirement",
            "employer_termination": "employer_termination",
            "mutual": "mutual",
            "other": "other",
        }[self.offboarding_type]

    def action_refresh_contract_status(self):
        require_offboarding_officer(self)
        self.ensure_one()
        if not self._employment_contract_model():
            self.with_context(**{self._CASE_EVIDENCE_CONTEXT: True}).write(
                {"contract_termination_state": "not_installed", "contract_res_id": False, "contract_reference": False}
            )
            return True
        contract = self._resolve_employment_contract()
        if not contract:
            self.with_context(**{self._CASE_EVIDENCE_CONTEXT: True}).write(
                {"contract_termination_state": "not_started", "contract_res_id": False, "contract_reference": False}
            )
            return True
        state = "not_started"
        if getattr(contract, "state", False) == "terminated" or getattr(contract, "terminated_at", False):
            state = "terminated"
        elif getattr(contract, "termination_review_state", False) == "pending":
            state = "pending"
        elif getattr(contract, "termination_review_state", False) == "approved":
            state = "approved"
        elif getattr(contract, "termination_review_state", False) == "rejected":
            state = "rejected"
        self.with_context(**{self._CASE_EVIDENCE_CONTEXT: True}).write(
            {
                "contract_termination_state": state,
                "contract_res_id": contract.id,
                "contract_reference": contract.display_name,
            }
        )
        return True

    def action_sync_contract_termination(self):
        require_offboarding_manager(self)
        self.ensure_one()
        if not self._employment_contract_model():
            raise UserError(_("OneHR Employment Contract is not installed. Mark the contract gate Not Applicable only when governance permits."))
        contract = self._resolve_employment_contract()
        if not contract:
            raise UserError(_("No governed OneHR Employment Contract record was found for this employee."))
        values = {
            "termination_type": self._map_contract_termination_type(),
            "termination_effective_date": self.approved_exit_date or self.proposed_exit_date,
            "termination_reason": self.exit_reason_notes or dict(self._fields["offboarding_type"].selection).get(self.offboarding_type),
        }
        contract.write(values)
        if getattr(contract, "termination_review_state", "none") in ("none", "rejected"):
            contract.action_request_termination_review()
        self.with_context(**{self._CASE_EVIDENCE_CONTEXT: True}).write(
            {"contract_res_id": contract.id, "contract_reference": contract.display_name, "contract_termination_state": "pending"}
        )
        return open_record_action(name=_("Employment Contract"), res_model=contract._name, res_id=contract.id)

    def action_execute_contract_termination(self):
        require_offboarding_manager(self)
        self.ensure_one()
        contract = self._resolve_employment_contract()
        if not contract:
            raise UserError(_("No governed OneHR Employment Contract record is linked/found."))
        contract.action_execute_termination()
        self.action_refresh_contract_status()
        return True

    def action_open_employment_contract(self):
        require_offboarding_officer(self)
        self.ensure_one()
        contract = self._resolve_employment_contract()
        if not contract:
            raise UserError(_("No governed OneHR Employment Contract record is available."))
        return open_record_action(name=_("Employment Contract"), res_model=contract._name, res_id=contract.id)

    def action_mark_contract_not_applicable(self):
        require_offboarding_manager(self)
        for record in self:
            if not record.contract_exception_note:
                raise UserError(_("Document the Contract Exception Note before marking this gate Not Applicable."))
            record.with_context(**{record._CASE_EVIDENCE_CONTEXT: True}).write({"contract_termination_state": "not_applicable"})
        return True

    # ------------------------------------------------------------------
    # Completion and closure
    # ------------------------------------------------------------------
    def action_complete(self):
        require_offboarding_manager(self)
        self.ensure_one()
        if self.state != "in_progress":
            raise UserError(_("Only an In Progress case can be completed."))
        blockers = self._readiness_blockers()
        if blockers:
            raise UserError(_("Completion blocked: %s") % "; ".join(blockers))
        self.with_context(**{self._CASE_STATE_CONTEXT: True, self._CASE_EVIDENCE_CONTEXT: True}).write(
            {"state": "completed", "completed_at": fields.Datetime.now(), "completed_by_id": self.env.user.id}
        )
        return True

    def action_close(self):
        require_offboarding_manager(self)
        self.ensure_one()
        if self.state != "completed":
            raise UserError(_("Only a Completed case can be Closed."))
        blockers = self._readiness_blockers()
        if blockers:
            raise UserError(_("Closure blocked: %s") % "; ".join(blockers))
        self.with_context(**{self._CASE_STATE_CONTEXT: True, self._CASE_EVIDENCE_CONTEXT: True}).write(
            {
                "state": "closed",
                "effective_exit_date": self.approved_exit_date or self.proposed_exit_date,
                "closed_at": fields.Datetime.now(),
                "closed_by_id": self.env.user.id,
                "cycle_days": ((self.approved_exit_date or self.proposed_exit_date) - self.request_date).days if self.request_date and (self.approved_exit_date or self.proposed_exit_date) else 0,
            }
        )
        return True

    def action_cancel(self):
        require_offboarding_manager(self)
        for record in self:
            if record.state in ("completed", "closed"):
                raise UserError(_("Completed or Closed cases cannot be cancelled."))
            record.with_context(**{record._CASE_STATE_CONTEXT: True}).write({"state": "cancelled"})
        return True

    def action_archive_employee_master(self):
        require_offboarding_admin(self)
        if not self.env.su and not self.env.user.has_group("hr.group_hr_manager"):
            raise AccessError(_("HR Manager authority is additionally required to archive the employee master."))
        for record in self:
            if record.state != "closed":
                raise UserError(_("Employee master archival is allowed only after the offboarding case is Closed."))
            record.employee_id.write({"active": False})
        return True

    # ------------------------------------------------------------------
    # Navigation and downstream service contracts
    # ------------------------------------------------------------------
    def action_open_employee(self):
        self.ensure_one()
        return open_record_action(name=self.employee_id.display_name, res_model="hr.employee", res_id=self.employee_id.id)

    def action_open_checklist(self):
        self.ensure_one()
        return open_records_action(
            name=_("Clearance Tasks — %s", self.name),
            res_model="onehr.offboarding.checklist",
            domain=[("offboarding_id", "=", self.id)],
            context={"default_offboarding_id": self.id},
            view_mode="kanban,list,form,calendar",
        )

    def action_open_exit_interview(self):
        self.ensure_one()
        if not self.exit_interview_ids:
            return self.action_create_exit_interview()
        return open_record_action(name=_("Exit Interview"), res_model="onehr.exit.interview", res_id=self.exit_interview_ids[:1].id)

    def action_print_clearance_summary(self):
        self.ensure_one()
        return self.env.ref("onehr_retirement_offboarding.action_report_offboarding_clearance").report_action(self)

    def onehr_offboarding_portal_payload(self):
        """Employee-facing sanitized service data. Portal owns HTTP/session/access."""
        self.ensure_one()
        self.check_access("read")
        return {
            "reference": self.name,
            "employee_id": self.employee_id.id,
            "state": self.state,
            "offboarding_type": self.offboarding_type,
            "proposed_exit_date": str(self.proposed_exit_date or ""),
            "approved_exit_date": str(self.approved_exit_date or ""),
            "completion_percent": self.completion_percent,
            "open_mandatory_tasks": self.mandatory_open_count,
            "exit_interview_state": self.exit_interview_ids[:1].state if self.exit_interview_ids else False,
        }

    def onehr_offboarding_api_payload(self):
        self.ensure_one()
        payload = self.onehr_offboarding_portal_payload()
        payload.update(
            {
                "company_id": self.company_id.id,
                "branch_scope_key": self.branch_scope_key or False,
                "access_state": self.access_state,
                "final_benefit_state": self.final_benefit_state,
                "contract_termination_state": self.contract_termination_state,
            }
        )
        return payload

    def onehr_offboarding_document_payload(self):
        self.ensure_one()
        self.check_access("read")
        return {
            "reference": self.name,
            "employee_id": self.employee_id.id,
            "employee_name": self.employee_id.name,
            "company_id": self.company_id.id,
            "offboarding_type": self.offboarding_type,
            "effective_exit_date": str(self.approved_exit_date or self.proposed_exit_date or ""),
            "source_model": self._name,
            "source_res_id": self.id,
        }

    @api.model
    def onehr_offboarding_kpi_snapshot(self, company=None, date_from=None, date_to=None):
        """Narrow Analytics service; persistence/dashboard ownership stays Analytics."""
        self.check_access("read")
        company = company or self.env.company
        domain = [("company_id", "=", company.id)]
        if date_from:
            domain.append(("request_date", ">=", date_from))
        if date_to:
            domain.append(("request_date", "<=", date_to))
        cases = self.search(domain)
        closed = cases.filtered(lambda c: c.state == "closed")
        cycle_days = []
        for case in closed:
            if case.request_date and case.effective_exit_date:
                cycle_days.append((case.effective_exit_date - case.request_date).days)
        reasons = Counter(cases.mapped("exit_reason_code"))
        return {
            "company_id": company.id,
            "case_count": len(cases),
            "closed_count": len(closed),
            "open_count": len(cases - closed),
            "retirement_count": len(cases.filtered(lambda c: c.offboarding_type == "retirement")),
            "resignation_count": len(cases.filtered(lambda c: c.offboarding_type == "resignation")),
            "overdue_task_count": sum(cases.mapped("overdue_task_count")),
            "average_time_to_close_days": round(sum(cycle_days) / len(cycle_days), 2) if cycle_days else 0.0,
            "exit_reason_distribution": {key or "unspecified": value for key, value in sorted(reasons.items(), key=lambda x: str(x[0]))},
        }

    @api.model
    def _cron_remind_due_clearance(self):
        """Daily bounded SLA reminder. No automatic business completion/retry loop."""
        today = fields.Date.context_today(self)
        horizon = today + timedelta(days=1)
        tasks = self.env["onehr.offboarding.checklist"].search(
            [
                ("state", "in", ["pending", "in_progress", "blocked"]),
                ("due_date", "!=", False),
                ("due_date", "<=", horizon),
                ("assigned_user_id", "!=", False),
            ]
        )
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        for task in tasks:
            duplicate = task.activity_ids.filtered(
                lambda a: a.activity_type_id == activity_type
                and a.user_id == task.assigned_user_id
                and a.date_deadline == task.due_date
            )
            if duplicate:
                continue
            task.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=task.assigned_user_id.id,
                date_deadline=task.due_date,
                summary=_("Offboarding clearance due: %s", task.title),
                note=_("Case %s for %s requires clearance action.", task.offboarding_id.name, task.employee_id.name),
            )
        return True

import json

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .action_helpers import display_notification, open_record_action
from .authority_helpers import require_payroll_manager, require_payroll_officer


class OneHRPayrollImport(models.Model):
    """Vendor payroll-result evidence for one employee within one Export batch.

    Corrections are revisioned within this same Registry-approved model. Finalized
    rows are never overwritten; a governed correction supersedes the prior revision.
    """

    _name = "onehr.payroll.import"
    _description = "OneHR Payroll Imported Result"
    _inherit = ["onehr.mixin.audit"]
    _order = "export_id desc, employee_number_snapshot, external_reference, revision desc, id desc"
    _rec_name = "name"

    _STATE_CONTEXT = "onehr_payroll_import_state_controlled"
    _EVIDENCE_CONTEXT = "onehr_payroll_import_evidence_controlled"
    _SNAPSHOT_CONTEXT = "onehr_payroll_import_snapshot_controlled"

    name = fields.Char(
        string="Import No.",
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: _("New"),
        index=True,
        tracking=True,
    )
    export_id = fields.Many2one(
        "onehr.payroll.export",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    config_id = fields.Many2one(
        "onehr.payroll.bridge.config",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        required=True,
        ondelete="restrict",
        tracking=True,
    )

    employee_id = fields.Many2one(
        "hr.employee",
        ondelete="restrict",
        index=True,
        tracking=True,
    )
    employee_number_snapshot = fields.Char(required=True, index=True, tracking=True)
    employee_name_snapshot = fields.Char(readonly=True, copy=False, index=True)
    department_id = fields.Many2one("hr.department", readonly=True, copy=False, ondelete="restrict", index=True)
    department_snapshot = fields.Char(readonly=True, copy=False, index=True)
    grade_code_snapshot = fields.Char(readonly=True, copy=False)
    position_code_snapshot = fields.Char(readonly=True, copy=False)

    period_start = fields.Date(related="export_id.period_start", store=True, readonly=True, index=True)
    period_end = fields.Date(related="export_id.period_end", store=True, readonly=True, index=True)

    external_reference = fields.Char(required=True, index=True, tracking=True)
    payslip_number = fields.Char(index=True, tracking=True)
    payment_date = fields.Date(index=True, tracking=True)
    source_channel = fields.Selection(
        [("csv", "CSV"), ("api", "API"), ("manual", "Manual")],
        required=True,
        default="manual",
        index=True,
        tracking=True,
    )

    gross_amount = fields.Monetary(currency_field="currency_id", tracking=True)
    deduction_amount = fields.Monetary(currency_field="currency_id", tracking=True)
    net_amount = fields.Monetary(currency_field="currency_id", tracking=True)
    employer_cost = fields.Monetary(currency_field="currency_id", tracking=True)
    net_equation_delta = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_net_equation",
    )

    raw_payload_json = fields.Text(
        groups="onehr_payroll_bridge.group_onehr_payroll_officer,onehr_payroll_bridge.group_onehr_payroll_manager",
    )
    validation_message = fields.Text(readonly=True, copy=False)

    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("validated", "Validated"),
            ("reconciled", "Reconciled"),
            ("error", "Error"),
            ("superseded", "Superseded"),
        ],
        required=True,
        default="draft",
        index=True,
        tracking=True,
    )
    revision = fields.Integer(required=True, default=1, readonly=True, copy=False)
    supersedes_id = fields.Many2one(
        "onehr.payroll.import",
        ondelete="restrict",
        readonly=True,
        copy=False,
        index=True,
    )
    superseded_by_ids = fields.One2many(
        "onehr.payroll.import",
        "supersedes_id",
        string="Correction Revisions",
        readonly=True,
    )
    is_current_revision = fields.Boolean(
        compute="_compute_is_current_revision",
        store=True,
        index=True,
    )

    imported_at = fields.Datetime(readonly=True, copy=False)
    imported_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    validated_at = fields.Datetime(readonly=True, copy=False)
    validated_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")
    reconciled_at = fields.Datetime(readonly=True, copy=False)
    reconciled_by_id = fields.Many2one("res.users", readonly=True, copy=False, ondelete="restrict")

    _external_revision_unique = models.Constraint(
        "unique(export_id, external_reference, revision)",
        "Payroll Import external reference/revision must be unique within an Export.",
    )

    @api.onchange("export_id")
    def _onchange_export_id(self):
        if self.export_id:
            self.config_id = self.export_id.config_id
            self.company_id = self.export_id.company_id
            self.currency_id = self.export_id.currency_id

    @api.onchange("employee_id")
    def _onchange_employee_id(self):
        if self.employee_id:
            self.employee_number_snapshot = self.employee_id.onehr_employee_number or ""

    @api.model_create_multi
    def create(self, vals_list):
        require_payroll_officer(self)
        prepared = []
        for incoming in vals_list:
            values = dict(incoming)
            evidence_controlled = self.env.context.get(self._EVIDENCE_CONTEXT)
            if not evidence_controlled and (
                values.get("supersedes_id") or int(values.get("revision") or 1) != 1
            ):
                raise AccessError(
                    _("Payroll Import revision lineage can be created only by the governed correction action.")
                )
            export = self.env["onehr.payroll.export"].browse(values.get("export_id")).exists()
            if not export:
                raise ValidationError(_("A valid Payroll Export is required."))
            if export.state != "posted":
                raise ValidationError(
                    _("Payroll Import evidence can be created only for a Posted Payroll Export.")
                )
            values.setdefault("config_id", export.config_id.id)
            values.setdefault("company_id", export.company_id.id)
            values.setdefault("currency_id", export.currency_id.id)
            if values["config_id"] != export.config_id.id or values["company_id"] != export.company_id.id:
                raise ValidationError(_("Import Configuration/Company must match its Payroll Export."))
            if values.get("state", "draft") != "draft" and not self.env.context.get(self._STATE_CONTEXT):
                raise AccessError(_("Payroll Imports must be created in Draft."))
            if values.get("name", _("New")) == _("New"):
                values["name"] = self.env["ir.sequence"].next_by_code("onehr.payroll.import") or _("New")
            employee = self.env["hr.employee"].browse(values.get("employee_id")).exists()
            if employee:
                values.setdefault("employee_number_snapshot", employee.onehr_employee_number or "")
                values.setdefault("employee_name_snapshot", employee.name)
                values.setdefault("department_id", employee.department_id.id or False)
                values.setdefault("department_snapshot", employee.department_id.name or "")
                grade = employee.onehr_grade_id
                position = employee.onehr_primary_position_id
                values.setdefault(
                    "grade_code_snapshot",
                    grade.code if grade and "code" in grade._fields else "",
                )
                values.setdefault(
                    "position_code_snapshot",
                    position.code if position and "code" in position._fields else "",
                )
            values.setdefault("imported_at", fields.Datetime.now())
            values.setdefault("imported_by_id", self.env.user.id)
            prepared.append(values)
        records = super().create(prepared)
        records._validate_basic_integrity()
        records._refresh_employee_snapshots()
        return records

    def write(self, values):
        state_controlled = self.env.context.get(self._STATE_CONTEXT)
        evidence_controlled = self.env.context.get(self._EVIDENCE_CONTEXT)
        snapshot_controlled = self.env.context.get(self._SNAPSHOT_CONTEXT)

        if "state" in values and not state_controlled:
            raise AccessError(_("Payroll Import state changes only through governed actions."))

        anchor_fields = {"name", "export_id", "config_id", "company_id", "revision", "supersedes_id"}
        if anchor_fields & set(values) and not evidence_controlled:
            raise AccessError(_("Payroll Import identity and revision anchors cannot be rewritten."))

        evidence_fields = {
            "employee_name_snapshot",
            "department_id",
            "department_snapshot",
            "grade_code_snapshot",
            "position_code_snapshot",
            "revision",
            "supersedes_id",
            "imported_at",
            "imported_by_id",
            "validated_at",
            "validated_by_id",
            "reconciled_at",
            "reconciled_by_id",
            "validation_message",
        }
        if evidence_fields & set(values) and not evidence_controlled:
            raise AccessError(_("Payroll Import evidence is controlled by business actions."))

        editable_fields = {
            "employee_id",
            "employee_number_snapshot",
            "external_reference",
            "payslip_number",
            "payment_date",
            "source_channel",
            "gross_amount",
            "deduction_amount",
            "net_amount",
            "employer_cost",
            "currency_id",
            "raw_payload_json",
        }
        if editable_fields & set(values):
            if any(record.state not in {"draft", "error"} for record in self):
                raise AccessError(
                    _("Validated/Reconciled payroll results are immutable. Create a governed correction revision.")
                )
            require_payroll_officer(self)

        result = super().write(values)
        if editable_fields & set(values):
            self._validate_basic_integrity()
            if not snapshot_controlled:
                self._refresh_employee_snapshots()
        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_governed_import(self):
        if any(
            record.state != "draft"
            or record.supersedes_id
            or record.superseded_by_ids
            for record in self
        ):
            raise AccessError(_("Only an original, unused Draft Payroll Import may be deleted."))

    @api.constrains(
        "export_id",
        "config_id",
        "company_id",
        "employee_id",
        "employee_number_snapshot",
        "gross_amount",
        "deduction_amount",
        "net_amount",
        "employer_cost",
        "revision",
    )
    def _check_basic_integrity(self):
        self._validate_basic_integrity()

    def _validate_basic_integrity(self):
        for record in self:
            if record.export_id:
                if record.config_id != record.export_id.config_id:
                    raise ValidationError(_("Payroll Import Configuration must match its Export."))
                if record.company_id != record.export_id.company_id:
                    raise ValidationError(_("Payroll Import Company must match its Export."))
            if record.employee_id and record.employee_id.company_id != record.company_id:
                raise ValidationError(_("Payroll Import employee must belong to the same company."))
            if record.revision <= 0:
                raise ValidationError(_("Payroll Import Revision must be positive."))
            if record.deduction_amount < 0:
                raise ValidationError(_("Deduction Amount cannot be negative."))
            if record.employer_cost < 0:
                raise ValidationError(_("Employer Cost cannot be negative."))
        return True

    def _refresh_employee_snapshots(self):
        for record in self:
            if not record.employee_id:
                continue
            grade = record.employee_id.onehr_grade_id
            position = record.employee_id.onehr_primary_position_id
            vals = {
                "employee_number_snapshot": record.employee_id.onehr_employee_number or record.employee_number_snapshot,
                "employee_name_snapshot": record.employee_id.name,
                "department_id": record.employee_id.department_id.id or False,
                "department_snapshot": record.employee_id.department_id.name or "",
                "grade_code_snapshot": grade.code if grade and "code" in grade._fields else "",
                "position_code_snapshot": position.code if position and "code" in position._fields else "",
            }
            record.with_context(
                **{
                    self._EVIDENCE_CONTEXT: True,
                    self._SNAPSHOT_CONTEXT: True,
                }
            ).write(vals)
        return True

    @api.depends("superseded_by_ids")
    def _compute_is_current_revision(self):
        for record in self:
            record.is_current_revision = not bool(record.superseded_by_ids)

    @api.depends("gross_amount", "deduction_amount", "net_amount")
    def _compute_net_equation(self):
        for record in self:
            record.net_equation_delta = record.gross_amount - record.deduction_amount - record.net_amount

    def _validation_error(self):
        self.ensure_one()
        if not self.employee_id:
            return _("Employee Number does not resolve to an employee in the Export company.")
        if self.employee_id.onehr_employee_number != self.employee_number_snapshot:
            return _("Employee Number snapshot does not match the selected employee.")
        if not self.external_reference:
            return _("External Reference is required.")
        if self.currency_id != self.export_id.currency_id:
            return _("Vendor result currency must match the Payroll Export currency.")
        if not self.is_current_revision:
            return _("A superseded Payroll Import revision cannot be validated.")
        policy = self.export_id._frozen_reconciliation_policy()
        if policy["validate_net_equation"]:
            tolerance = policy["net_reconciliation_tolerance"]
            if abs(self.net_equation_delta) > tolerance:
                return _(
                    "Gross - Deductions differs from Net by %(delta).2f, exceeding tolerance %(tolerance).2f.",
                    delta=self.net_equation_delta,
                    tolerance=tolerance,
                )
        source_numbers = self.export_id._source_employee_numbers()
        if source_numbers and self.employee_number_snapshot not in source_numbers:
            return _("Employee Number was not present in the frozen Payroll Export source rows.")
        return ""

    def action_validate(self):
        self.ensure_one()
        require_payroll_officer(self)
        if self.export_id.state != "posted":
            raise UserError(_("Payroll Import validation requires a Posted Payroll Export."))
        if self.state not in {"draft", "error"}:
            raise UserError(_("Only Draft/Error current imports can be validated."))
        error = self._validation_error()
        values = {
            "validation_message": error,
            "state": "error" if error else "validated",
        }
        if not error:
            values.update(
                {
                    "validated_at": fields.Datetime.now(),
                    "validated_by_id": self.env.user.id,
                }
            )
        self.with_context(
            **{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}
        ).write(values)
        if error:
            return display_notification(error, notification_type="warning", sticky=True)
        return display_notification(_("Payroll result validated."))

    def action_create_correction(self):
        self.ensure_one()
        require_payroll_manager(self)
        if self.state == "reconciled":
            raise UserError(
                _("Reconciled payroll evidence cannot be corrected inside the closed Export. Create a new payroll correction cycle.")
            )
        if not self.is_current_revision:
            raise UserError(_("Only the current payroll import revision can be superseded."))

        correction = self.with_context(
            **{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}
        ).copy(
            {
                "state": "draft",
                "revision": self.revision + 1,
                "supersedes_id": self.id,
                "validation_message": False,
                "validated_at": False,
                "validated_by_id": False,
                "reconciled_at": False,
                "reconciled_by_id": False,
                "imported_at": fields.Datetime.now(),
                "imported_by_id": self.env.user.id,
            }
        )
        self.with_context(
            **{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}
        ).write({"state": "superseded"})
        return open_record_action(
            name=correction.display_name,
            res_model=self._name,
            res_id=correction.id,
        )

    def _mark_reconciled(self):
        require_payroll_manager(self)
        for record in self:
            if record.state != "validated" or not record.is_current_revision:
                raise UserError(_("Only current Validated payroll results can be reconciled."))
        self.with_context(
            **{self._STATE_CONTEXT: True, self._EVIDENCE_CONTEXT: True}
        ).write(
            {
                "state": "reconciled",
                "reconciled_at": fields.Datetime.now(),
                "reconciled_by_id": self.env.user.id,
            }
        )
        return True

    def action_open_export(self):
        self.ensure_one()
        require_payroll_officer(self)
        return open_record_action(
            name=self.export_id.display_name,
            res_model="onehr.payroll.export",
            res_id=self.export_id.id,
        )

    def action_open_employee(self):
        self.ensure_one()
        require_payroll_officer(self)
        if not self.employee_id:
            raise UserError(_("Resolve the employee before opening the Employee record."))
        return open_record_action(
            name=self.employee_id.display_name,
            res_model="hr.employee",
            res_id=self.employee_id.id,
        )

    def onehr_portal_payslip_payload(self):
        """Employee-safe result payload; callers remain subject to normal ACL/rules."""
        self.ensure_one()
        return {
            "import_id": self.id,
            "employee_id": self.employee_id.id if self.employee_id else False,
            "period_start": fields.Date.to_string(self.period_start),
            "period_end": fields.Date.to_string(self.period_end),
            "payslip_number": self.payslip_number,
            "payment_date": fields.Date.to_string(self.payment_date) if self.payment_date else False,
            "gross_amount": self.gross_amount,
            "deduction_amount": self.deduction_amount,
            "net_amount": self.net_amount,
            "currency": self.currency_id.name,
            "state": self.state,
        }

    @api.model
    def onehr_ingest_payroll_result(self, payload):
        """Stable API adapter service without authentication/credential ownership."""
        require_payroll_officer(self)
        values = dict(payload or {})
        export = self.env["onehr.payroll.export"].browse(values.get("export_id")).exists()
        if not export:
            raise ValidationError(_("Payroll result ingestion requires a valid export_id."))
        employee_number = (values.get("employee_number") or "").strip()
        external_reference = (values.get("external_reference") or "").strip()
        if not employee_number or not external_reference:
            raise ValidationError(_("Payroll result ingestion requires employee_number and external_reference."))

        employee = self.env["hr.employee"].search(
            [
                ("company_id", "=", export.company_id.id),
                ("onehr_employee_number", "=", employee_number),
            ],
            limit=1,
        )
        current = self.search(
            [
                ("export_id", "=", export.id),
                ("external_reference", "=", external_reference),
                ("is_current_revision", "=", True),
            ],
            order="revision desc, id desc",
            limit=1,
        )
        incoming = {
            "export_id": export.id,
            "config_id": export.config_id.id,
            "company_id": export.company_id.id,
            "currency_id": export.currency_id.id,
            "employee_id": employee.id or False,
            "employee_number_snapshot": employee_number,
            "external_reference": external_reference,
            "payslip_number": values.get("payslip_number") or "",
            "payment_date": values.get("payment_date") or False,
            "gross_amount": float(values.get("gross_amount") or 0.0),
            "deduction_amount": float(values.get("deduction_amount") or 0.0),
            "net_amount": float(values.get("net_amount") or 0.0),
            "employer_cost": float(values.get("employer_cost") or 0.0),
            "source_channel": "api",
            "raw_payload_json": json.dumps(values, ensure_ascii=False, sort_keys=True, default=str),
        }
        if current and current.state in {"draft", "error"}:
            current.with_context(
                onehr_payroll_import_evidence_controlled=True
            ).write(incoming)
            return current
        if current:
            return current
        return self.create(incoming)

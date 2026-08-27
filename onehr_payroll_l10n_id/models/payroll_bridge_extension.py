import json

from odoo import _, fields, models
from odoo.exceptions import AccessError, UserError

from .action_helpers import open_record_action, open_records_action


class OneHRPayrollExportIndonesiaLocalization(models.Model):
    """Freeze reviewed Indonesian localization parameters into Payroll Bridge evidence."""

    _inherit = "onehr.payroll.export"

    _L10N_EVIDENCE_CONTEXT = "onehr_payroll_l10n_evidence_controlled"

    onehr_l10n_param_id = fields.Many2one(
        "onehr.payroll.l10n.param",
        string="Indonesia Payroll Parameters",
        ondelete="restrict",
        readonly=True,
        copy=False,
        index=True,
    )
    onehr_l10n_snapshot_json = fields.Text(
        string="Frozen Indonesia Localization Snapshot",
        readonly=True,
        copy=False,
        groups="onehr_payroll_bridge.group_onehr_payroll_manager",
    )
    onehr_l10n_sha256 = fields.Char(
        string="Indonesia Localization SHA-256",
        readonly=True,
        copy=False,
        index=True,
    )

    def write(self, values):
        l10n_evidence_fields = {
            "onehr_l10n_param_id",
            "onehr_l10n_snapshot_json",
            "onehr_l10n_sha256",
        }
        if (
            l10n_evidence_fields & set(values)
            and not self.env.context.get(self._L10N_EVIDENCE_CONTEXT)
        ):
            raise AccessError(
                _("Indonesia payroll localization evidence is controlled by Payroll Export actions.")
            )
        return super().write(values)

    def _resolve_onehr_l10n_param(self):
        self.ensure_one()
        if not self.period_end:
            raise UserError(_("Payroll Period End is required before resolving Indonesia localization."))
        return self.env["onehr.payroll.l10n.param"].onehr_find_effective_parameter(
            self.company_id,
            self.period_end,
            require_review=True,
        )

    def action_generate_export(self):
        """Bind localization before base row generation so the source hash covers its reference."""
        self.ensure_one()
        if self.state != "draft":
            return super().action_generate_export()

        parameter = self._resolve_onehr_l10n_param()
        payload = parameter.onehr_parameter_payload(
            as_of_date=self.period_end,
            require_review=True,
        )
        snapshot = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        self.with_context(**{self._L10N_EVIDENCE_CONTEXT: True}).write(
            {
                "onehr_l10n_param_id": parameter.id,
                "onehr_l10n_snapshot_json": snapshot,
                "onehr_l10n_sha256": payload["parameter_sha256"],
            }
        )
        return super().action_generate_export()

    def _onehr_extend_employee_export_row(self, employee, row):
        row = super()._onehr_extend_employee_export_row(employee, row)
        if self.onehr_l10n_param_id:
            variables = row.setdefault("variables_json", {})
            variables["indonesia_localization"] = {
                "parameter_id": self.onehr_l10n_param_id.id,
                "code": self.onehr_l10n_param_id.code,
                "revision": self.onehr_l10n_param_id.revision,
                "sha256": self.onehr_l10n_sha256,
            }
        return row

    def action_reset_generation(self):
        self.ensure_one()
        result = super().action_reset_generation()
        self.with_context(**{self._L10N_EVIDENCE_CONTEXT: True}).write(
            {
                "onehr_l10n_param_id": False,
                "onehr_l10n_snapshot_json": False,
                "onehr_l10n_sha256": False,
            }
        )
        return result

    def onehr_payroll_export_payload(self):
        payload = super().onehr_payroll_export_payload()
        self.ensure_one()
        if self.onehr_l10n_snapshot_json:
            try:
                payload["indonesia_localization"] = json.loads(
                    self.onehr_l10n_snapshot_json
                )
            except ValueError as exc:
                raise UserError(
                    _("Frozen Indonesia localization snapshot is invalid JSON.")
                ) from exc
        return payload

    def action_open_onehr_l10n_param(self):
        self.ensure_one()
        if not self.env.user.has_group("onehr_payroll_bridge.group_onehr_payroll_manager"):
            raise AccessError(_("Only a Payroll Manager may open Indonesia statutory parameters."))
        if not self.onehr_l10n_param_id:
            raise UserError(_("Generate the Payroll Export to bind Indonesia localization parameters."))
        return open_record_action(
            name=self.onehr_l10n_param_id.display_name,
            res_model="onehr.payroll.l10n.param",
            res_id=self.onehr_l10n_param_id.id,
        )


class OneHRPayrollBridgeConfigIndonesiaLocalization(models.Model):
    """Manager navigation from Payroll Bridge configuration to localization history."""

    _inherit = "onehr.payroll.bridge.config"

    def action_open_indonesia_localization(self):
        self.ensure_one()
        if not self.env.user.has_group("onehr_payroll_bridge.group_onehr_payroll_manager"):
            raise AccessError(_("Only a Payroll Manager may manage Indonesia statutory parameters."))
        return open_records_action(
            name=_("Indonesia Payroll Localization — %s") % self.company_id.display_name,
            res_model="onehr.payroll.l10n.param",
            domain=[("company_id", "=", self.company_id.id)],
            context={"default_company_id": self.company_id.id},
            view_mode="list,calendar,form",
        )


from odoo import api, fields, models
from odoo.exceptions import AccessError
from ..services.contracts import CONTRACT_BY_KEY

class OneHRDemoGenerator(models.Model):
    _name = "onehr.demo.generator"
    _description = "OneHR Demo Generator Registry"
    _order = "sequence, phase, key, id"

    _unique_key = models.Constraint("UNIQUE(key)", "OneHR Demo generator key must be unique.")

    key = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    phase = fields.Integer(required=True, index=True)
    sequence = fields.Integer(required=True, index=True)
    active = fields.Boolean(default=True)
    implemented = fields.Boolean(default=False, readonly=True, index=True)
    implementation_state = fields.Selection([
        ("planned","Planned"),("implemented","Implemented"),("frozen","PASS / Frozen"),("blocked","Blocked")
    ], required=True, default="planned", readonly=True, index=True)
    side_effect_classification = fields.Selection([
        ("SAFE_INTERNAL","Safe Internal"),
        ("SAFE_WITH_DEMO_CONTEXT","Safe with Demo Context"),
        ("DISABLED_FOR_DEMO","Disabled for Demo"),
        ("REQUIRES_STUB/LOCAL_ENDPOINT","Requires Stub / Local Endpoint"),
        ("PROHIBITED","Prohibited"),
        ("UNVERIFIED","Unverified"),
    ], required=True, default="UNVERIFIED", readonly=True)
    reset_policy = fields.Selection([
        ("DELETE_SAFE","Delete Safe"),
        ("REVERSE_BY_BUSINESS_ACTION","Reverse by Business Action"),
        ("ARCHIVE_ONLY","Archive Only"),
        ("REUSE_ON_REBUILD","Reuse on Rebuild"),
        ("IMMUTABLE_PROTECTED","Immutable / Protected"),
        ("UNVERIFIED","Unverified"),
    ], required=True, default="UNVERIFIED", readonly=True)
    contract_digest = fields.Char(required=True, readonly=True, index=True)
    prerequisite_keys = fields.Text(compute="_compute_contract_details")
    supported_profiles = fields.Char(compute="_compute_contract_details")
    required_addons = fields.Text(compute="_compute_contract_details")
    required_models = fields.Text(compute="_compute_contract_details")
    required_groups = fields.Text(compute="_compute_contract_details")
    contract_json = fields.Text(compute="_compute_contract_details")

    @api.depends("key")
    def _compute_contract_details(self):
        import json
        for record in self:
            contract = CONTRACT_BY_KEY.get(record.key) or {}
            record.prerequisite_keys = ", ".join(contract.get("prerequisites", [])) or "—"
            record.supported_profiles = ", ".join(contract.get("profiles", [])) or "—"
            record.required_addons = ", ".join(contract.get("addons", [])) or "—"
            record.required_models = ", ".join(sorted(contract.get("models", {}))) or "—"
            record.required_groups = ", ".join(contract.get("groups", [])) or "—"
            record.contract_json = json.dumps(contract, indent=2, sort_keys=True, default=str)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.is_superuser():
            raise AccessError("Generator Registry is code-owned and cannot be created manually.")
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.is_superuser():
            raise AccessError("Generator Registry is code-owned and cannot be edited manually.")
        return super().write(vals)

    def unlink(self):
        if not self.env.is_superuser():
            raise AccessError("Generator Registry is code-owned and cannot be deleted manually.")
        return super().unlink()

    def action_open_generator(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": self.display_name,
            "res_model": "onehr.demo.generator",
            "res_id": self.id,
            "view_mode": "form",
            "target": "current",
        }


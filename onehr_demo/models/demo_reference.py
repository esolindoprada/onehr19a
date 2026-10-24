
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError
from ..services.authority import require_demo_admin
from ..services.contracts import CONTRACT_BY_KEY, REFERENCE_TARGET_MODELS

class OneHRDemoReference(models.Model):
    _name = "onehr.demo.reference"
    _description = "OneHR Demo Provenance Reference"
    _rec_name = "stable_key"
    _order = "scenario_id, stable_key, id"
    _check_company_auto = True

    _unique_scenario_key = models.Constraint(
        "UNIQUE(scenario_id, stable_key)", "A deterministic demo key can map to only one reference in a scenario."
    )

    scenario_id = fields.Many2one("onehr.demo.scenario", required=True, ondelete="cascade", index=True, check_company=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True)
    generator_id = fields.Many2one("onehr.demo.generator", required=True, ondelete="restrict", index=True)
    generator_key = fields.Char(required=True, readonly=True, index=True)
    run_id = fields.Many2one("onehr.demo.run", required=True, ondelete="restrict", index=True, check_company=True)
    stable_key = fields.Char(required=True, readonly=True, index=True)
    target_model = fields.Char(required=True, readonly=True, index=True)
    target_res_id = fields.Integer(required=True, readonly=True, index=True)
    target_display_name = fields.Char(readonly=True)
    disposition = fields.Selection([
        ("created","Created"),("reused","Reused"),("updated","Updated")
    ], required=True, readonly=True, index=True)
    reset_policy = fields.Selection([
        ("DELETE_SAFE","Delete Safe"),
        ("REVERSE_BY_BUSINESS_ACTION","Reverse by Business Action"),
        ("ARCHIVE_ONLY","Archive Only"),
        ("REUSE_ON_REBUILD","Reuse on Rebuild"),
        ("IMMUTABLE_PROTECTED","Immutable / Protected"),
        ("UNVERIFIED","Unverified"),
    ], required=True, readonly=True, index=True)
    state = fields.Selection([
        ("active","Active"),("invalidated","Invalidated"),("protected","Protected")
    ], required=True, default="active", readonly=True, index=True)
    originating_run_id = fields.Many2one("onehr.demo.run", required=True, ondelete="restrict", readonly=True, check_company=True)
    source_compatibility_fingerprint = fields.Char(readonly=True, index=True)
    created_at = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    last_seen_at = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True)
    last_seen_run_id = fields.Many2one("onehr.demo.run", required=True, ondelete="restrict", readonly=True, check_company=True)

    @api.model_create_multi
    def create(self, vals_list):
        require_demo_admin(self.env)
        if not self.env.context.get("onehr_demo_reference_controlled"):
            raise AccessError(_("Demo references are created only by fixed business generators."))
        allowed_models = set(REFERENCE_TARGET_MODELS)
        for vals in vals_list:
            if vals.get("generator_key") not in CONTRACT_BY_KEY:
                raise ValidationError(_("Unknown fixed generator key in demo provenance."))
            if vals.get("target_model") not in allowed_models:
                raise ValidationError(_("Target model is outside the fixed OneHR Demo reference allow-list."))
        return super().create(vals_list)

    def write(self, vals):
        require_demo_admin(self.env)
        if not self.env.context.get("onehr_demo_reference_controlled"):
            raise AccessError(_("Demo references are system-controlled."))
        if "target_model" in vals and vals["target_model"] not in set(REFERENCE_TARGET_MODELS):
            raise ValidationError(_("Target model is outside the fixed OneHR Demo reference allow-list."))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("Demo references are retained/inactivated, not manually deleted."))

    @api.model
    def register_reference(self, *, scenario, generator_key, stable_key, target, run, disposition, reset_policy):
        require_demo_admin(self.env)
        if generator_key not in CONTRACT_BY_KEY:
            raise ValidationError(_("Unknown fixed generator key: %s") % generator_key)
        if not target or len(target) != 1 or target._name not in set(REFERENCE_TARGET_MODELS):
            raise ValidationError(_("A valid fixed-contract target record is required."))
        generator = self.env["onehr.demo.generator"].search([("key","=",generator_key)], limit=1)
        if not generator:
            raise ValidationError(_("Generator metadata missing: %s") % generator_key)
        existing = self.search([("scenario_id","=",scenario.id),("stable_key","=",stable_key)], limit=1)
        values = {
            "scenario_id":scenario.id,
            "company_id":scenario.company_id.id,
            "generator_id":generator.id,
            "generator_key":generator_key,
            "run_id":run.id,
            "stable_key":stable_key,
            "target_model":target._name,
            "target_res_id":target.id,
            "target_display_name":target.display_name,
            "disposition":disposition,
            "reset_policy":reset_policy,
            "state":"active",
            "source_compatibility_fingerprint":scenario.compatibility_fingerprint,
            "last_seen_at":fields.Datetime.now(),
            "last_seen_run_id":run.id,
        }
        if existing:
            if existing.target_model != target._name or existing.target_res_id != target.id:
                raise ValidationError(
                    _("Deterministic key %(key)s is already mapped to %(model)s/%(res_id)s and cannot be silently remapped.")
                    % {"key":stable_key,"model":existing.target_model,"res_id":existing.target_res_id}
                )
            existing.with_context(onehr_demo_reference_controlled=True).write(values)
            return existing
        values["originating_run_id"] = run.id
        return self.with_context(onehr_demo_reference_controlled=True).create(values)

    def action_open_target(self):
        self.ensure_one()
        if self.target_model not in set(REFERENCE_TARGET_MODELS):
            raise UserError(_("This reference target is outside the fixed allow-list."))
        if self.target_model not in self.env.registry.models:
            raise UserError(_("Target model is no longer loaded: %s") % self.target_model)
        Model = self.env[self.target_model]
        Model.check_access("read")
        target = Model.browse(self.target_res_id).exists()
        if not target:
            raise UserError(_("The referenced target record no longer exists."))
        return {"type":"ir.actions.act_window","name":target.display_name,"res_model":self.target_model,
                "res_id":target.id,"view_mode":"form","target":"current"}

    def action_open_run(self):
        self.ensure_one()
        return {"type":"ir.actions.act_window","name":self.run_id.display_name,"res_model":"onehr.demo.run",
                "res_id":self.run_id.id,"view_mode":"form","target":"current"}



from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from ..services.authority import require_demo_admin

class OneHRDemoCheckpoint(models.Model):
    _name = "onehr.demo.checkpoint"
    _description = "OneHR Demo Generator Checkpoint"
    _order = "run_id desc, sequence, id"
    _check_company_auto = True

    _unique_run_generator = models.Constraint(
        "UNIQUE(run_id, generator_key)", "A run can contain only one checkpoint for the same generator."
    )

    run_id = fields.Many2one("onehr.demo.run", required=True, ondelete="cascade", index=True, check_company=True)
    scenario_id = fields.Many2one("onehr.demo.scenario", required=True, ondelete="cascade", index=True, check_company=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True)
    generator_id = fields.Many2one("onehr.demo.generator", required=True, ondelete="restrict", index=True)
    generator_key = fields.Char(required=True, readonly=True, index=True)
    sequence = fields.Integer(required=True, index=True)
    state = fields.Selection([
        ("pending","Pending"),("running","Running"),("pass","PASS"),("failed","Failed"),
        ("blocked","Blocked"),("skipped","Skipped")
    ], required=True, default="pending", readonly=True, index=True)
    attempt = fields.Integer(default=1, readonly=True)
    started_at = fields.Datetime(readonly=True)
    finished_at = fields.Datetime(readonly=True)
    duration_seconds = fields.Float(readonly=True)
    created_count = fields.Integer(readonly=True)
    reused_count = fields.Integer(readonly=True)
    updated_count = fields.Integer(readonly=True)
    skipped_count = fields.Integer(readonly=True)
    protected_count = fields.Integer(readonly=True)
    validation_summary = fields.Text(readonly=True)
    root_cause_classification = fields.Selection([
        ("HARNESS_FAILURE","Harness Failure"),
        ("ENVIRONMENT_FAILURE","Environment Failure"),
        ("ODOO_VERSION_COMPATIBILITY_FAILURE","Odoo Version Compatibility Failure"),
        ("ADDON_SOURCE_FAILURE","Addon Source Failure"),
        ("TEST_DEFECT","Test Defect"),
        ("DATA/MIGRATION_FAILURE","Data / Migration Failure"),
        ("ARCHITECTURE_CONFLICT","Architecture Conflict"),
    ], readonly=True, index=True)
    first_actionable_root_cause = fields.Text(readonly=True)
    technical_detail = fields.Text(readonly=True, groups="onehr_demo.group_onehr_demo_admin")

    @api.model_create_multi
    def create(self, vals_list):
        require_demo_admin(self.env)
        if not self.env.context.get("onehr_demo_controlled_create"):
            raise AccessError(_("Demo Checkpoints are created only by the orchestrator."))
        return super().create(vals_list)

    def write(self, vals):
        require_demo_admin(self.env)
        if not self.env.context.get("onehr_demo_controlled_write"):
            raise AccessError(_("Demo Checkpoint evidence is system-controlled."))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("Demo Checkpoint evidence is retained."))

    @api.model
    def _controlled_create(self, vals):
        return self.with_context(onehr_demo_controlled_create=True).create(vals)

    def _controlled_write(self, vals):
        return self.with_context(onehr_demo_controlled_write=True).write(vals)

    def action_open_run(self):
        self.ensure_one()
        return {"type":"ir.actions.act_window","name":self.run_id.display_name,"res_model":"onehr.demo.run",
                "res_id":self.run_id.id,"view_mode":"form","target":"current"}

    def action_open_generator(self):
        self.ensure_one()
        return self.generator_id.action_open_generator()


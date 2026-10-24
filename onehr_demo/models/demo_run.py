
from odoo import _, api, fields, models
from odoo.exceptions import AccessError
from ..services.authority import require_demo_admin

class OneHRDemoRun(models.Model):
    _name = "onehr.demo.run"
    _description = "OneHR Demo Run"
    _order = "started_at desc, id desc"
    _check_company_auto = True

    _unique_run_key = models.Constraint("UNIQUE(run_key)", "OneHR Demo run key must be unique.")

    name = fields.Char(required=True, default="New", readonly=True, index=True)
    run_key = fields.Char(readonly=True, index=True)
    scenario_id = fields.Many2one("onehr.demo.scenario", required=True, ondelete="cascade", index=True, check_company=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True)
    run_type = fields.Selection([
        ("compatibility","Compatibility"),("readiness","Readiness"),("generation","Generation"),
        ("validation","Validation"),("reset_preview","Reset Preview"),("reset","Reset"),
    ], required=True, index=True)
    profile = fields.Selection([("quick","Quick"),("standard","Standard"),("full","Full Enterprise")], required=True, index=True)
    reference_date = fields.Date(required=True)
    reference_datetime = fields.Datetime(required=True)
    timezone = fields.Char(required=True)
    deterministic_seed = fields.Integer(required=True)
    scenario_version = fields.Char(required=True)
    source_compatibility_fingerprint = fields.Char(index=True)
    state = fields.Selection([
        ("pending","Pending"),("running","Running"),("pass","PASS"),("failed","Failed"),("blocked","Blocked"),
    ], required=True, default="pending", readonly=True, index=True)
    operator_id = fields.Many2one("res.users", required=True, default=lambda self:self.env.user, ondelete="restrict", index=True)
    started_at = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True, index=True)
    finished_at = fields.Datetime(readonly=True)
    created_count = fields.Integer(readonly=True)
    reused_count = fields.Integer(readonly=True)
    updated_count = fields.Integer(readonly=True)
    skipped_count = fields.Integer(readonly=True)
    protected_count = fields.Integer(readonly=True)
    checkpoint_ids = fields.One2many("onehr.demo.checkpoint","run_id",readonly=True)
    checkpoint_count = fields.Integer(compute="_compute_checkpoint_count")
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
    result_summary = fields.Text(readonly=True)

    @api.depends("checkpoint_ids")
    def _compute_checkpoint_count(self):
        for record in self:
            record.checkpoint_count = len(record.checkpoint_ids)

    @api.model_create_multi
    def create(self, vals_list):
        require_demo_admin(self.env)
        if not self.env.context.get("onehr_demo_controlled_create"):
            raise AccessError(_("Demo Runs are created only by Demo Control Center actions."))
        records = super().create(vals_list)
        for record in records:
            record._controlled_write({
                "name": f"{record.run_type.upper()}-{record.id:08d}",
                "run_key": f"{record.scenario_id.code}.run.{record.run_type}.{record.id:08d}",
            })
        return records

    def write(self, vals):
        require_demo_admin(self.env)
        if not self.env.context.get("onehr_demo_controlled_write"):
            raise AccessError(_("Demo Run evidence is system-controlled."))
        return super().write(vals)

    def unlink(self):
        raise AccessError(_("Demo Run evidence is retained and cannot be deleted."))

    @api.model
    def _controlled_create(self, vals):
        return self.with_context(onehr_demo_controlled_create=True).create(vals)

    def _controlled_write(self, vals):
        return self.with_context(onehr_demo_controlled_write=True).write(vals)

    def action_open_checkpoints(self):
        self.ensure_one()
        return {
            "type":"ir.actions.act_window",
            "name":_("Checkpoints — %s") % self.display_name,
            "res_model":"onehr.demo.checkpoint",
            "view_mode":"list,form",
            "domain":[("run_id","=",self.id)],
            "context":{"create":False},
        }



from odoo import api, fields, models
from odoo.exceptions import AccessError
from ..services.authority import require_demo_admin
from ..services.sanitization import sanitize_text

class OneHRDemoLog(models.Model):
    _name = "onehr.demo.log"
    _description = "OneHR Demo Operational Log"
    _rec_name = "message"
    _order = "event_at desc, id desc"
    _check_company_auto = True

    scenario_id = fields.Many2one("onehr.demo.scenario", required=True, ondelete="cascade", index=True, check_company=True)
    company_id = fields.Many2one("res.company", required=True, ondelete="restrict", index=True)
    run_id = fields.Many2one("onehr.demo.run", ondelete="set null", index=True, check_company=True)
    generator_id = fields.Many2one("onehr.demo.generator", ondelete="set null", index=True)
    generator_key = fields.Char(index=True)
    event_at = fields.Datetime(required=True, default=fields.Datetime.now, readonly=True, index=True)
    severity = fields.Selection([("info","Info"),("warning","Warning"),("error","Error")],
                                required=True, default="info", readonly=True, index=True)
    category = fields.Selection([
        ("compatibility","Compatibility"),("readiness","Readiness"),("generation","Generation"),
        ("validation","Validation"),("reset","Reset"),("security","Security"),("system","System")
    ], required=True, readonly=True, index=True)
    root_cause_classification = fields.Selection([
        ("HARNESS_FAILURE","Harness Failure"),
        ("ENVIRONMENT_FAILURE","Environment Failure"),
        ("ODOO_VERSION_COMPATIBILITY_FAILURE","Odoo Version Compatibility Failure"),
        ("ADDON_SOURCE_FAILURE","Addon Source Failure"),
        ("TEST_DEFECT","Test Defect"),
        ("DATA/MIGRATION_FAILURE","Data / Migration Failure"),
        ("ARCHITECTURE_CONFLICT","Architecture Conflict"),
    ], readonly=True, index=True)
    message = fields.Char(required=True, readonly=True)
    technical_detail = fields.Text(readonly=True, groups="onehr_demo.group_onehr_demo_admin")

    @api.model_create_multi
    def create(self, vals_list):
        require_demo_admin(self.env)
        if not self.env.context.get("onehr_demo_log_controlled"):
            raise AccessError("Demo logs are written only by controlled platform operations.")
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            vals["message"] = sanitize_text(vals.get("message"), limit=500)
            vals["technical_detail"] = sanitize_text(vals.get("technical_detail"), limit=4000)
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        raise AccessError("OneHR Demo operational logs are immutable.")

    def unlink(self):
        raise AccessError("OneHR Demo operational logs are retained.")

    @api.model
    def log_event(self, **values):
        require_demo_admin(self.env)
        return self.with_context(onehr_demo_log_controlled=True).create(values)


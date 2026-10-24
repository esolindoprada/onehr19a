
import json
import re
import pytz

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from ..services.authority import require_demo_admin, require_system_demo_admin
from ..services.compatibility import CompatibilityAudit
from ..services.contracts import (
    AUTHORITATIVE_SOURCE_LABEL,
    AUTHORITATIVE_SOURCE_SHA256,
    GENERATOR_CONTRACTS,
    GOVERNING_MASTER_PROMPT_SHA256,
    IMPLEMENTED_GENERATOR_KEYS,
    ROOT_GUARDRAIL_SHA256,
    SEQUENCE_POLICIES,
)
from ..services.deterministic import stable_demo_key
from ..services.orchestrator import (
    DemoOrchestrator,
    classify_generator_exception,
    implemented_readiness_blockers,
)
from ..services.reset import DemoResetService
from ..services.sanitization import sanitize_text


class OneHRDemoScenario(models.Model):
    _name = "onehr.demo.scenario"
    _description = "OneHR Enterprise Demo Scenario"
    _order = "company_id, code, id"
    _check_company_auto = True

    _unique_code_company = models.Constraint(
        "UNIQUE(company_id, code)",
        "OneHR Demo scenario code must be unique within a company.",
    )

    name = fields.Char(required=True, index=True)
    code = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        "res.company", required=True, default=lambda self: self.env.company,
        ondelete="restrict", index=True
    )
    profile = fields.Selection(
        [("quick","QUICK"),("standard","STANDARD"),("full","FULL ENTERPRISE")],
        required=True, default="quick", index=True
    )
    profile_version = fields.Char(required=True, default="1.0")
    scenario_version = fields.Char(required=True, default="1.0.0")
    reference_date = fields.Date(required=True, default=lambda self: fields.Date.to_date("2026-09-01"))
    reference_datetime = fields.Datetime(
        required=True,
        default=lambda self: fields.Datetime.to_datetime("2026-09-01 02:00:00"),
        help="Frozen business reference clock. Default equals 09:00 Asia/Jakarta.",
    )
    timezone = fields.Selection(selection="_timezone_selection", required=True, default="Asia/Jakarta")
    locale = fields.Char(required=True, default="id_ID")
    country_code = fields.Char(required=True, default="ID")
    deterministic_seed = fields.Integer(required=True, default=247)

    state = fields.Selection(
        [
            ("draft","Draft"),
            ("compatibility_required","Compatibility Required"),
            ("incompatible","Incompatible"),
            ("compatible","Compatible"),
            ("readiness_failed","Readiness Failed"),
            ("ready","Ready"),
            ("generating","Generating"),
            ("paused_failed","Paused / Failed"),
            ("generated","Generated"),
            ("validating","Validating"),
            ("validated","Validated"),
            ("reset_previewed","Reset Previewed"),
            ("resetting","Resetting"),
            ("reset","Reset"),
        ],
        required=True, default="compatibility_required", readonly=True, index=True
    )

    safety_acknowledged = fields.Boolean(
        default=False,
        help="Explicit acknowledgement that this scenario is for a NON-PRODUCTION demo/test database."
    )
    generation_enabled = fields.Boolean(
        default=False, readonly=True,
        help="Bulk generation/reset remains disabled until explicitly enabled."
    )

    compatibility_status = fields.Selection(
        [
            ("unverified","Unverified"),
            ("compatible","Compatible"),
            ("incompatible","Incompatible"),
            ("stale","Stale"),
            ("blocked","Blocked"),
        ],
        required=True, default="unverified", readonly=True, index=True
    )
    compatibility_fingerprint = fields.Char(readonly=True, index=True)
    compatibility_checked_at = fields.Datetime(readonly=True)
    compatibility_checked_by_id = fields.Many2one("res.users", readonly=True)
    compatibility_failure_count = fields.Integer(readonly=True)
    compatibility_first_root_cause = fields.Text(readonly=True)
    compatibility_evidence_json = fields.Text(readonly=True, groups="onehr_demo.group_onehr_demo_admin")

    readiness_status = fields.Selection(
        [("unverified","Unverified"),("ready","Ready"),("blocked","Blocked"),("failed","Failed")],
        required=True, default="unverified", readonly=True, index=True
    )
    readiness_checked_at = fields.Datetime(readonly=True)
    readiness_checked_by_id = fields.Many2one("res.users", readonly=True)
    readiness_message = fields.Text(readonly=True)

    validation_status = fields.Selection(
        [
            ("not_run","Not Run"),
            ("structural_pass","Structural PASS"),
            ("business_pass","Business Integrity PASS"),
            ("security_pass","Security PASS"),
            ("analytics_pass","Analytics Traceability PASS"),
            ("certified","Full Enterprise Certified"),
        ],
        required=True, default="not_run", readonly=True, index=True
    )

    authoritative_source_label = fields.Char(required=True, default=AUTHORITATIVE_SOURCE_LABEL, readonly=True)
    authoritative_source_sha256 = fields.Char(required=True, default=AUTHORITATIVE_SOURCE_SHA256, readonly=True)
    governing_master_prompt_sha256 = fields.Char(required=True, default=GOVERNING_MASTER_PROMPT_SHA256, readonly=True)
    root_guardrail_sha256 = fields.Char(required=True, default=ROOT_GUARDRAIL_SHA256, readonly=True)

    run_ids = fields.One2many("onehr.demo.run", "scenario_id", readonly=True)
    checkpoint_ids = fields.One2many("onehr.demo.checkpoint", "scenario_id", readonly=True)
    reference_ids = fields.One2many("onehr.demo.reference", "scenario_id", readonly=True)
    log_ids = fields.One2many("onehr.demo.log", "scenario_id", readonly=True)

    run_count = fields.Integer(compute="_compute_operational_summary")
    checkpoint_count = fields.Integer(compute="_compute_operational_summary")
    reference_count = fields.Integer(compute="_compute_operational_summary")
    log_count = fields.Integer(compute="_compute_operational_summary")
    failed_checkpoint_count = fields.Integer(compute="_compute_operational_summary")
    latest_run_id = fields.Many2one("onehr.demo.run", compute="_compute_operational_summary")
    current_failed_checkpoint_id = fields.Many2one("onehr.demo.checkpoint", compute="_compute_operational_summary")
    planned_generator_count = fields.Integer(compute="_compute_registry_summary")
    implemented_generator_count = fields.Integer(compute="_compute_registry_summary")
    deterministic_sequence_policy_count = fields.Integer(compute="_compute_registry_summary")
    generation_available = fields.Boolean(compute="_compute_registry_summary")
    generation_progress = fields.Float(compute="_compute_generation_progress")
    completed_generator_count = fields.Integer(compute="_compute_model_by_model_state")
    pending_generator_count = fields.Integer(compute="_compute_model_by_model_state")
    failed_generator_count = fields.Integer(compute="_compute_model_by_model_state")
    next_generator_key = fields.Char(compute="_compute_model_by_model_state")
    next_generator_name = fields.Char(compute="_compute_model_by_model_state")
    next_generator_phase = fields.Integer(compute="_compute_model_by_model_state")
    next_generator_implemented = fields.Boolean(compute="_compute_model_by_model_state")
    model_by_model_progress = fields.Float(compute="_compute_model_by_model_state")

    @api.model
    def _timezone_selection(self):
        return [(zone, zone) for zone in pytz.all_timezones]

    @api.depends("run_ids", "checkpoint_ids", "reference_ids", "log_ids", "checkpoint_ids.state")
    def _compute_operational_summary(self):
        for scenario in self:
            scenario.run_count = len(scenario.run_ids)
            scenario.checkpoint_count = len(scenario.checkpoint_ids)
            scenario.reference_count = len(scenario.reference_ids)
            scenario.log_count = len(scenario.log_ids)
            failed = scenario.checkpoint_ids.filtered(lambda row: row.state == "failed")
            scenario.failed_checkpoint_count = len(failed)
            scenario.current_failed_checkpoint_id = failed.sorted(key=lambda row: row.id, reverse=True)[:1]
            scenario.latest_run_id = scenario.run_ids.sorted(key=lambda row: row.id, reverse=True)[:1]

    def _compute_registry_summary(self):
        for scenario in self:
            scenario.planned_generator_count = len(GENERATOR_CONTRACTS)
            scenario.implemented_generator_count = len(IMPLEMENTED_GENERATOR_KEYS)
            scenario.deterministic_sequence_policy_count = len(SEQUENCE_POLICIES)
            scenario.generation_available = bool(IMPLEMENTED_GENERATOR_KEYS)

    @api.depends("checkpoint_ids.state", "run_ids.run_type")
    def _compute_generation_progress(self):
        total = max(1, len(GENERATOR_CONTRACTS))
        for scenario in self:
            generation_runs = scenario.run_ids.filtered(lambda row: row.run_type == "generation")
            latest = generation_runs.sorted(key=lambda row: row.id, reverse=True)[:1]
            if not latest:
                scenario.generation_progress = 0.0
                continue
            passed = len(latest.checkpoint_ids.filtered(lambda row: row.state in ("pass","skipped")))
            scenario.generation_progress = (passed / total) * 100.0

    @api.depends("checkpoint_ids.state", "checkpoint_ids.generator_key")
    def _compute_model_by_model_state(self):
        ordered = tuple(sorted(GENERATOR_CONTRACTS, key=lambda row: (row["phase"], row["key"])))
        Checkpoint = self.env["onehr.demo.checkpoint"]
        for scenario in self:
            passed_keys = set(Checkpoint.search([
                ("scenario_id", "=", scenario.id), ("state", "=", "pass")
            ]).mapped("generator_key"))
            failed_keys = set(Checkpoint.search([
                ("scenario_id", "=", scenario.id), ("state", "=", "failed")
            ]).mapped("generator_key"))
            completed = len([row for row in ordered if row["key"] in passed_keys])
            scenario.completed_generator_count = completed
            scenario.pending_generator_count = max(0, len(ordered) - completed)
            scenario.failed_generator_count = len(failed_keys)
            next_row = None
            for row in ordered:
                if row["key"] not in passed_keys:
                    next_row = row
                    break
            scenario.next_generator_key = next_row["key"] if next_row else False
            scenario.next_generator_name = next_row["name"] if next_row else False
            scenario.next_generator_phase = next_row["phase"] if next_row else 0
            scenario.next_generator_implemented = bool(next_row and next_row["key"] in IMPLEMENTED_GENERATOR_KEYS)
            scenario.model_by_model_progress = (completed / max(1, len(ordered))) * 100.0

    @api.constrains("code")
    def _check_code(self):
        pattern = re.compile(r"^[a-z][a-z0-9_.-]{2,47}$")
        for scenario in self:
            if not pattern.fullmatch((scenario.code or "").strip().lower()):
                raise ValidationError(
                    _("Scenario code must contain lowercase letters, digits, dot, underscore or hyphen (3-48 chars).")
                )

    @api.constrains("deterministic_seed")
    def _check_seed(self):
        for scenario in self:
            if not 0 <= scenario.deterministic_seed <= 2147483647:
                raise ValidationError(_("Deterministic seed must be between 0 and 2147483647."))

    @api.model_create_multi
    def create(self, vals_list):
        require_demo_admin(self.env)
        prepared = []
        for incoming in vals_list:
            vals = dict(incoming)
            if vals.get("code"):
                vals["code"] = vals["code"].strip().lower()
            vals.update({
                "state":"compatibility_required",
                "compatibility_status":"unverified",
                "readiness_status":"unverified",
                "generation_enabled":False,
            })
            prepared.append(vals)
        return super().create(prepared)

    def write(self, vals):
        require_demo_admin(self.env)
        if "state" in vals and not self.env.context.get("onehr_demo_state_controlled"):
            raise AccessError(_("Use Demo Control Center actions to change lifecycle state."))
        if "generation_enabled" in vals and not self.env.context.get("onehr_demo_evidence_controlled"):
            raise AccessError(_("Use the explicit NON-PRODUCTION enable/disable action."))

        identity_fields = {
            "code","company_id","profile","profile_version","scenario_version","reference_date",
            "reference_datetime","timezone","locale","country_code","deterministic_seed",
        }
        identity_change_fields = identity_fields.intersection(vals)
        if identity_change_fields and not self.env.context.get("onehr_demo_evidence_controlled"):
            for scenario in self:
                if scenario.reference_ids:
                    raise ValidationError(
                        _("Scenario identity is frozen after demo provenance exists. "
                          "Create a new scenario for a different code/company/profile/reference clock/seed.")
                    )
        identity_changed = bool(
            identity_change_fields and not self.env.context.get("onehr_demo_evidence_controlled")
        )
        result = super().write(vals)
        if identity_changed:
            for scenario in self:
                stale_status = "stale" if scenario.compatibility_checked_at else "unverified"
                super(OneHRDemoScenario, scenario.with_context(
                    onehr_demo_state_controlled=True,
                    onehr_demo_evidence_controlled=True,
                )).write({
                    "state":"compatibility_required",
                    "compatibility_status":stale_status,
                    "compatibility_fingerprint":False,
                    "readiness_status":"unverified",
                    "readiness_message":"Scenario identity changed. Refresh Source Compatibility.",
                })
        return result

    def unlink(self):
        require_demo_admin(self.env)
        for scenario in self:
            if scenario.run_ids or scenario.reference_ids or scenario.log_ids:
                raise AccessError(_("A Demo Scenario with execution/provenance evidence cannot be deleted. Archive it instead."))
        return super().unlink()

    def _controlled_write(self, values):
        return self.with_context(
            onehr_demo_state_controlled=True,
            onehr_demo_evidence_controlled=True,
        ).write(values)

    def _new_run(self, run_type):
        self.ensure_one()
        return self.env["onehr.demo.run"]._controlled_create({
            "scenario_id":self.id,
            "company_id":self.company_id.id,
            "run_type":run_type,
            "profile":self.profile,
            "reference_date":self.reference_date,
            "reference_datetime":self.reference_datetime,
            "timezone":self.timezone,
            "deterministic_seed":self.deterministic_seed,
            "scenario_version":self.scenario_version,
            "source_compatibility_fingerprint":self.compatibility_fingerprint or False,
            "state":"running",
            "operator_id":self.env.user.id,
            "started_at":fields.Datetime.now(),
        })

    def _log(self, *, category, message, run=None, severity="info",
             root_cause_classification=False, technical_detail=False):
        self.ensure_one()
        return self.env["onehr.demo.log"].log_event(
            scenario_id=self.id,
            company_id=self.company_id.id,
            run_id=run.id if run else False,
            severity=severity,
            category=category,
            root_cause_classification=root_cause_classification or False,
            message=message,
            technical_detail=technical_detail or False,
        )

    def deterministic_key(self, domain, entity, stable_key):
        self.ensure_one()
        return stable_demo_key(self.code, domain, entity, stable_key)

    def _classify_compatibility_failure(self, failure):
        key = (failure or {}).get("key","")
        if key.startswith("framework.module_operation") or key.startswith("governance.root_guardrail"):
            return "ENVIRONMENT_FAILURE"
        if key.startswith(("module.","source_manifest.","source_fingerprint.","sequence.")):
            return "ODOO_VERSION_COMPATIBILITY_FAILURE"
        if any(marker in key for marker in (".field.",".method.",".selection.",".xmlid.",".group.")):
            return "ODOO_VERSION_COMPATIBILITY_FAILURE"
        return "ADDON_SOURCE_FAILURE"

    def action_enable_demo_generation(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        if not self.safety_acknowledged:
            raise UserError(_("Tick the NON-PRODUCTION acknowledgement before enabling Demo Generation."))
        self._controlled_write({
            "generation_enabled":True,
            "readiness_status":"unverified",
            "readiness_message":"Demo Generation enabled. Validate Readiness.",
        })
        self._log(category="security", message="NON-PRODUCTION Demo Generation explicitly enabled.")
        return self._notification(_("Demo Generation Enabled"),
                                  _("Generation/reset is enabled for this acknowledged demo scenario."),
                                  "warning", reload_form=True)

    def action_disable_demo_generation(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        self._controlled_write({
            "generation_enabled":False,
            "readiness_status":"blocked",
            "readiness_message":"Demo Generation is disabled.",
        })
        self._log(category="security", message="NON-PRODUCTION Demo Generation explicitly disabled.")
        return self._notification(_("Demo Generation Disabled"), _("Generation/reset is blocked."), "info", reload_form=True)

    def action_refresh_compatibility(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        if self.state in ("generating","validating","resetting"):
            raise UserError(_("Finish the active demo operation before refreshing compatibility."))

        run = self._new_run("compatibility")
        result = CompatibilityAudit(self.env, self).run()
        first = result["first_failure"]
        classification = self._classify_compatibility_failure(first) if first else False
        compatible = bool(result["compatible"])

        self._controlled_write({
            "authoritative_source_label": AUTHORITATIVE_SOURCE_LABEL,
            "authoritative_source_sha256": AUTHORITATIVE_SOURCE_SHA256,
            "governing_master_prompt_sha256": GOVERNING_MASTER_PROMPT_SHA256,
            "root_guardrail_sha256": ROOT_GUARDRAIL_SHA256,
            "compatibility_status":"compatible" if compatible else "incompatible",
            "compatibility_fingerprint":result["fingerprint"],
            "compatibility_checked_at":fields.Datetime.now(),
            "compatibility_checked_by_id":self.env.user.id,
            "compatibility_failure_count":result["failure_count"],
            "compatibility_first_root_cause":f"{first['key']}: {first['detail']}" if first else False,
            "compatibility_evidence_json":json.dumps(result["evidence"],indent=2,sort_keys=True,default=str),
            "readiness_status":"unverified",
            "readiness_message":"Compatibility PASS. Validate Readiness before generation."
                                if compatible else
                                "Compatibility failed. Review the complete evidence set before another native trial.",
            "state":"compatible" if compatible else "incompatible",
        })

        run._controlled_write({
            "state":"pass" if compatible else "failed",
            "finished_at":fields.Datetime.now(),
            "source_compatibility_fingerprint":result["fingerprint"],
            "root_cause_classification":classification or False,
            "first_actionable_root_cause":sanitize_text(
                f"{first['key']}: {first['detail']}", 1200
            ) if first else False,
            "result_summary":f"Whole-path compatibility {'PASS' if compatible else 'FAILED'}; "
                             f"{result['failure_count']} required failure(s); "
                             f"{len(result['checks'])} total checks.",
        })

        failed_rows = [row for row in result["checks"]
                       if row["status"] in ("INCOMPATIBLE","BLOCKED","UNVERIFIED")]
        self._log(
            category="compatibility",
            run=run,
            severity="info" if compatible else "error",
            root_cause_classification=classification,
            message=f"Whole-path compatibility {'PASS' if compatible else 'FAILED'} — "
                    f"{result['failure_count']} required failure(s) across {len(result['checks'])} checks.",
            technical_detail="All required source/runtime capability contracts passed."
                             if compatible else json.dumps(failed_rows, indent=2, sort_keys=True),
        )

        if compatible:
            return self._notification(
                _("Source Compatibility PASS"),
                _("%(count)s whole-path checks completed with no required failure.")
                % {"count":len(result["checks"])},
                "success", sticky=True, reload_form=True
            )
        return self._notification(
            _("Source Compatibility Failed"),
            _("%(count)s required contract(s) failed. First actionable root cause: %(first)s. "
              "All failures from the same audit are retained in Compatibility Evidence and Logs.")
            % {"count":result["failure_count"], "first":self.compatibility_first_root_cause or _("Unknown")},
            "danger", sticky=True, reload_form=True
        )

    def action_validate_readiness(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        if self.compatibility_status != "compatible" or not self.compatibility_fingerprint:
            raise UserError(_("Refresh Source Compatibility and obtain PASS first."))

        audit = CompatibilityAudit(self.env, self).run()
        if not audit["compatible"] or audit["fingerprint"] != self.compatibility_fingerprint:
            first = audit["first_failure"]
            self._controlled_write({
                "compatibility_status":"incompatible" if not audit["compatible"] else "stale",
                "compatibility_fingerprint":audit["fingerprint"],
                "compatibility_failure_count":audit["failure_count"],
                "compatibility_first_root_cause":f"{first['key']}: {first['detail']}" if first
                                                 else "Compatibility fingerprint changed.",
                "readiness_status":"blocked",
                "readiness_message":"Compatibility changed during readiness validation. Refresh Source Compatibility.",
                "state":"compatibility_required",
            })
            return self._notification(
                _("Readiness Blocked"),
                _("Source/runtime compatibility changed during readiness validation. Refresh Source Compatibility."),
                "danger", sticky=True, reload_form=True,
            )

        blockers = []
        if not self.safety_acknowledged:
            blockers.append("NON-PRODUCTION acknowledgement is not checked.")
        if not self.generation_enabled:
            blockers.append("Demo Generation is not explicitly enabled.")

        # Do not wait for a native create() traceback. Audit the complete authority
        # and company preconditions of every currently executable generator first.
        blockers.extend(implemented_readiness_blockers(self))

        run = self._new_run("readiness")
        if blockers:
            message = " ".join(blockers)
            self._controlled_write({
                "readiness_status":"blocked",
                "readiness_checked_at":fields.Datetime.now(),
                "readiness_checked_by_id":self.env.user.id,
                "readiness_message":message,
                "state":"readiness_failed",
            })
            run._controlled_write({
                "state":"blocked","finished_at":fields.Datetime.now(),
                "root_cause_classification":"ENVIRONMENT_FAILURE",
                "first_actionable_root_cause":message,
                "result_summary":"Readiness blocked by NON-PRODUCTION safety gate.",
            })
            self._log(category="readiness",run=run,severity="warning",
                      root_cause_classification="ENVIRONMENT_FAILURE",message=message)
            return self._notification(_("Readiness Blocked"), _(message), "warning", sticky=True, reload_form=True)

        message = (
            f"READINESS PASS for MP02-MP05: all {len(GENERATOR_CONTRACTS)} whole-path "
            f"generator contracts and {len(SEQUENCE_POLICIES)} explicit production-sequence policies "
            f"are compatible; {len(IMPLEMENTED_GENERATOR_KEYS)} bounded business generator(s) "
            "have executable handler, validator, authority and reset contracts."
        )
        self._controlled_write({
            "readiness_status":"ready",
            "readiness_checked_at":fields.Datetime.now(),
            "readiness_checked_by_id":self.env.user.id,
            "readiness_message":message,
            "state":"ready",
        })
        run._controlled_write({"state":"pass","finished_at":fields.Datetime.now(),"result_summary":message})
        self._log(category="readiness",run=run,message=message)
        return self._notification(_("Readiness PASS"), _(message), "success", sticky=True, reload_form=True)

    def _assert_generation_ready(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        if not self.safety_acknowledged or not self.generation_enabled:
            raise UserError(_("NON-PRODUCTION safety acknowledgement and enablement are required."))
        if self.compatibility_status != "compatible" or self.readiness_status != "ready":
            raise UserError(_("Compatibility and Readiness must both be PASS."))
        if not self.generation_available:
            raise UserError(_("No bounded business generator is implemented for this release."))

    def _generate_selected_profile(self, required_profile):
        self.ensure_one()
        if self.profile != required_profile:
            raise UserError(
                _("This compatibility lock is for profile '%(current)s'. Change Dataset Profile to '%(required)s', "
                  "refresh compatibility, and validate readiness before generation.")
                % {"current":self.profile,"required":required_profile}
            )
        self._assert_generation_ready()
        run = self._new_run("generation")
        self._controlled_write({"state":"generating"})
        try:
            result = DemoOrchestrator(self, run).execute()
        except Exception as exc:
            failed_checkpoint = self.env["onehr.demo.checkpoint"].search([
                ("run_id", "=", run.id),
                ("state", "=", "failed"),
            ], order="id desc", limit=1)
            classification = (
                failed_checkpoint.root_cause_classification
                if failed_checkpoint else classify_generator_exception(exc)
            )
            first_cause = (
                failed_checkpoint.first_actionable_root_cause
                if failed_checkpoint else sanitize_text(exc, 1200)
            )
            run._controlled_write({
                "state":"failed",
                "finished_at":fields.Datetime.now(),
                "root_cause_classification":classification,
                "first_actionable_root_cause":first_cause,
                "result_summary":"Generation paused on the first actionable bounded failure; prior atomic generators remain reusable.",
            })
            self._controlled_write({"state":"paused_failed"})
            return self._notification(
                _("Generation Paused / Failed"),
                _(first_cause),
                "danger", sticky=True, reload_form=True,
            )
        run._controlled_write({
            "state":"pass",
            "finished_at":fields.Datetime.now(),
            "created_count":result.get("created",0),
            "reused_count":result.get("reused",0),
            "updated_count":result.get("updated",0),
            "skipped_count":result.get("skipped",0),
            "protected_count":result.get("protected",0),
            "result_summary":(
                f"Bounded generation PASS: created={result.get('created',0)}, "
                f"reused={result.get('reused',0)}, updated={result.get('updated',0)}, "
                f"skipped={result.get('skipped',0)}, protected={result.get('protected',0)}."
            ),
        })
        self._controlled_write({
            "state":"generated",
            "validation_status":"not_run",
        })
        self._log(
            category="generation",
            run=run,
            message=run.result_summary,
        )
        return self._notification(
            _("Generation PASS"),
            _(run.result_summary),
            "success",
            sticky=True,
            reload_form=True,
        )

    def action_execute_next_model(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        self._assert_generation_ready()
        if not self.next_generator_key:
            self._controlled_write({"state":"generated"})
            return self._notification(_("Model-by-Model Complete"), _("All frozen generator contracts are PASS."), "success", sticky=True, reload_form=True)
        if not self.next_generator_implemented:
            message = _("Next deterministic contract is %(key)s — %(name)s (MP%(phase)s). Its bounded producer is not implemented yet; the requirement remains registered and fail-closed.") % {
                "key":self.next_generator_key,"name":self.next_generator_name,"phase":self.next_generator_phase}
            self._log(category="generation", severity="warning", message=message, root_cause_classification="ARCHITECTURE_CONFLICT")
            self._controlled_write({"state":"paused_failed","readiness_message":message})
            return self._notification(_("Model-by-Model Blocked"), message, "warning", sticky=True, reload_form=True)
        run = self._new_run("generation")
        self._controlled_write({"state":"generating"})
        try:
            result = DemoOrchestrator(self, run).execute_generator(self.next_generator_key)
        except Exception as exc:
            failed = self.env["onehr.demo.checkpoint"].search([("run_id","=",run.id),("state","=","failed")], order="id desc", limit=1)
            first = failed.first_actionable_root_cause if failed else sanitize_text(exc, 1200)
            classification = failed.root_cause_classification if failed else classify_generator_exception(exc)
            run._controlled_write({"state":"failed","finished_at":fields.Datetime.now(),"root_cause_classification":classification,"first_actionable_root_cause":first,"result_summary":f"Model-by-model execution paused at {self.next_generator_key}."})
            self._controlled_write({"state":"paused_failed","readiness_message":first})
            return self._notification(_("Model-by-Model Failed"), first, "danger", sticky=True, reload_form=True)
        run._controlled_write({"state":"pass","finished_at":fields.Datetime.now(),"created_count":result.get("created",0),"reused_count":result.get("reused",0),"updated_count":result.get("updated",0),"skipped_count":result.get("skipped",0),"protected_count":result.get("protected",0),"result_summary":f"{self.next_generator_key} PASS — {result.get('summary','bounded generator completed')}."})
        remaining = self.next_generator_key
        self.invalidate_recordset()
        done_count = self.completed_generator_count
        total_count = len(GENERATOR_CONTRACTS)
        next_key = self.next_generator_key
        next_name = self.next_generator_name
        self._controlled_write({"state":"generated","validation_status":"not_run","readiness_message":f"Model-by-model PASS: {remaining}. Completed {done_count}/{total_count}. Next: {next_key or 'COMPLETE'} — {next_name or ''}"})
        self._log(category="generation", run=run, message=run.result_summary)
        return self._notification(_("Model-by-Model PASS"), run.result_summary, "success", sticky=True, reload_form=True)

    def action_execute_next_10(self):
        """Execute up to ten next deterministic model contracts in one bounded run.

        The batch is only an execution accelerator. It never changes contract order,
        never skips a failed/blocked journey, and never executes a planned producer.
        A runtime failure deliberately returns without a client reload so the operator
        can copy the exact actionable notification while the checkpoint/run evidence
        remains persisted server-side.
        """
        self.ensure_one()
        require_system_demo_admin(self.env)
        self._assert_generation_ready()

        if not self.next_generator_key:
            self._controlled_write({"state": "generated"})
            return self._notification(
                _("Execute Next 10 Complete"),
                _("All frozen generator contracts are PASS."),
                "success", sticky=True, reload_form=True,
            )

        run = self._new_run("generation")
        self._controlled_write({"state": "generating"})
        executed = []
        totals = {"created": 0, "reused": 0, "updated": 0, "skipped": 0, "protected": 0}

        for _index in range(10):
            self.invalidate_recordset()
            key = self.next_generator_key
            if not key:
                break

            if not self.next_generator_implemented:
                message = _("Execute Next 10 stopped after %(count)s model(s). Next deterministic contract is %(key)s — %(name)s (MP%(phase)s). Its bounded producer is not implemented yet; the requirement remains registered and fail-closed.") % {
                    "count": len(executed),
                    "key": self.next_generator_key,
                    "name": self.next_generator_name,
                    "phase": self.next_generator_phase,
                }
                run._controlled_write({
                    "state": "pass",
                    "finished_at": fields.Datetime.now(),
                    "created_count": totals["created"],
                    "reused_count": totals["reused"],
                    "updated_count": totals["updated"],
                    "skipped_count": totals["skipped"],
                    "protected_count": totals["protected"],
                    "result_summary": message,
                })
                self._log(category="generation", severity="warning", run=run, message=message, root_cause_classification="ARCHITECTURE_CONFLICT")
                self._controlled_write({"state": "paused_failed", "readiness_message": message})
                return self._notification(_("Execute Next 10 Stopped"), message, "warning", sticky=True, reload_form=False)

            try:
                result = DemoOrchestrator(self, run).execute_generator(key)
            except Exception as exc:
                failed = self.env["onehr.demo.checkpoint"].search([
                    ("run_id", "=", run.id), ("generator_key", "=", key), ("state", "=", "failed")
                ], order="id desc", limit=1)
                first = failed.first_actionable_root_cause if failed else sanitize_text(exc, 1600)
                classification = failed.root_cause_classification if failed else classify_generator_exception(exc)
                run._controlled_write({
                    "state": "failed",
                    "finished_at": fields.Datetime.now(),
                    "created_count": totals["created"],
                    "reused_count": totals["reused"],
                    "updated_count": totals["updated"],
                    "skipped_count": totals["skipped"],
                    "protected_count": totals["protected"],
                    "root_cause_classification": classification,
                    "first_actionable_root_cause": first,
                    "result_summary": f"Execute Next 10 stopped at {key} after {len(executed)} successful model(s).",
                })
                self._controlled_write({"state": "paused_failed", "readiness_message": first})
                self._log(
                    category="generation", severity="error", run=run,
                    message=f"Execute Next 10 stopped at {key}: {first}",
                    root_cause_classification=classification,
                    technical_detail=failed.technical_detail if failed else sanitize_text(exc, 3000),
                )
                # IMPORTANT: do not reload the form on failure. The red notification
                # must remain visible so the operator can copy it verbatim.
                return self._notification(_("Execute Next 10 Stopped"), first, "danger", sticky=True, reload_form=False)

            for counter in totals:
                totals[counter] += int(result.get(counter, 0))
            executed.append(key)

        run._controlled_write({
            "state": "pass",
            "finished_at": fields.Datetime.now(),
            "created_count": totals["created"],
            "reused_count": totals["reused"],
            "updated_count": totals["updated"],
            "skipped_count": totals["skipped"],
            "protected_count": totals["protected"],
            "result_summary": f"Execute Next 10 PASS — executed {len(executed)} model(s): {', '.join(executed)}.",
        })
        self.invalidate_recordset()
        if not self.next_generator_key:
            self._controlled_write({"state": "generated", "validation_status": "not_run", "readiness_message": f"Execute Next 10 PASS: completed {len(executed)} model(s). All frozen generator contracts are PASS."})
            self._log(category="generation", run=run, message=run.result_summary)
            return self._notification(_("Execute Next 10 PASS"), run.result_summary, "success", sticky=True, reload_form=True)

        if not self.next_generator_implemented:
            message = _("Execute Next 10 PASS — executed %(count)s model(s). Next: %(key)s — %(name)s (MP%(phase)s) is planned and remains fail-closed.") % {
                "count": len(executed), "key": self.next_generator_key,
                "name": self.next_generator_name, "phase": self.next_generator_phase,
            }
            self._controlled_write({"state": "paused_failed", "readiness_message": message})
            self._log(category="generation", severity="warning", run=run, message=message, root_cause_classification="ARCHITECTURE_CONFLICT")
            return self._notification(_("Execute Next 10 Stopped"), message, "warning", sticky=True, reload_form=False)

        message = _("Execute Next 10 PASS — executed %(count)s model(s). Next: %(key)s — %(name)s (MP%(phase)s).") % {
            "count": len(executed), "key": self.next_generator_key,
            "name": self.next_generator_name, "phase": self.next_generator_phase,
        }
        self._controlled_write({"state": "generated", "validation_status": "not_run", "readiness_message": message})
        self._log(category="generation", run=run, message=run.result_summary)
        return self._notification(_("Execute Next 10 PASS"), message, "success", sticky=True, reload_form=True)

    def action_generate_quick(self):
        return self.action_execute_next_model()

    def action_generate_standard(self):
        return self.action_execute_next_model()

    def action_generate_full(self):
        return self.action_execute_next_model()

    def action_continue_generation(self):
        return self.action_execute_next_model()

    def action_validate_dataset(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        if self.state != "generated":
            raise UserError(_("Generate the selected bounded dataset before validation."))
        if self.compatibility_status != "compatible":
            raise UserError(_("Source Compatibility must remain PASS before dataset validation."))

        run = self._new_run("validation")
        self._controlled_write({"state":"validating"})
        try:
            result = DemoOrchestrator(self, run).validate()
        except Exception as exc:
            failed_checkpoint = self.env["onehr.demo.checkpoint"].search([
                ("run_id", "=", run.id), ("state", "=", "failed")
            ], order="id desc", limit=1)
            classification = (
                failed_checkpoint.root_cause_classification
                if failed_checkpoint else classify_generator_exception(exc)
            )
            first_cause = (
                failed_checkpoint.first_actionable_root_cause
                if failed_checkpoint else sanitize_text(exc, 1200)
            )
            run._controlled_write({
                "state":"failed",
                "finished_at":fields.Datetime.now(),
                "root_cause_classification":classification,
                "first_actionable_root_cause":first_cause,
                "result_summary":"Dataset validation failed on the first bounded postcondition.",
            })
            self._controlled_write({
                "state":"paused_failed",
                "validation_status":"not_run",
            })
            return self._notification(
                _("Dataset Validation Failed"),
                _(first_cause),
                "danger", sticky=True, reload_form=True,
            )

        summary = (
            f"DATASET STRUCTURAL PASS for {result.get('validated_generators',0)} implemented "
            f"generator(s). {result.get('summary','')}"
        )
        run._controlled_write({
            "state":"pass",
            "finished_at":fields.Datetime.now(),
            "result_summary":summary,
        })
        self._controlled_write({
            "state":"validated",
            "validation_status":"structural_pass",
        })
        self._log(category="validation", run=run, message=summary)
        return self._notification(_("Dataset Validation PASS"), _(summary), "success", sticky=True, reload_form=True)

    def action_reset_preview(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        run = self._new_run("reset_preview")
        rows = DemoResetService(self).preview()
        protected = len([row for row in rows if row["planned_action"] == "PROTECTED_NO_HANDLER"])
        retained = len([row for row in rows if row["planned_action"] == "RETAIN_FOR_REBUILD"])
        message = (
            f"Reset Preview: {len(rows)} active provenance reference(s); "
            f"{retained} retained for deterministic rebuild; {protected} blocked/protected."
        )
        run._controlled_write({
            "state":"pass" if not protected else "blocked",
            "finished_at":fields.Datetime.now(),
            "protected_count":protected,
            "result_summary":message,
        })
        self._controlled_write({"state":"reset_previewed","readiness_message":message})
        self._log(category="reset",run=run,severity="warning" if protected else "info",
                  message=message,technical_detail=json.dumps(rows,indent=2,sort_keys=True))
        return self._notification(_("Reset Preview"), _(message), "warning" if protected else "info", sticky=True, reload_form=True)

    def action_reset_demo_dataset(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        if not self.generation_enabled or not self.safety_acknowledged:
            raise UserError(_("NON-PRODUCTION safety enablement is required for reset."))
        if self.state != "reset_previewed":
            raise UserError(_("Run Reset Preview immediately before reset."))
        run = self._new_run("reset")
        self._controlled_write({"state":"resetting"})
        try:
            result = DemoResetService(self).execute()
        except Exception as exc:
            classification = classify_generator_exception(exc)
            first_cause = sanitize_text(exc, 1200)
            run._controlled_write({
                "state":"failed",
                "finished_at":fields.Datetime.now(),
                "root_cause_classification":classification,
                "first_actionable_root_cause":first_cause,
                "result_summary":"Safe Reset failed; no partial reset is accepted.",
            })
            self._controlled_write({"state":"reset_previewed"})
            return self._notification(
                _("Safe Reset Failed"),
                _(first_cause),
                "danger", sticky=True, reload_form=True,
            )
        run._controlled_write({
            "state":"pass","finished_at":fields.Datetime.now(),
            "protected_count":result.get("protected",0),
            "result_summary":f"Reset processed {result.get('processed',0)} reference(s).",
        })
        self._controlled_write({
            "state":"reset",
            "readiness_status":"unverified",
            "validation_status":"not_run",
            "readiness_message":"Reset complete. Production masters classified REUSE_ON_REBUILD were retained; validate readiness before rebuild.",
        })
        return self._notification(_("Reset Complete"), _("Owned demo reset actions completed."), "success", sticky=True, reload_form=True)

    def action_rebuild_dataset(self):
        self.ensure_one()
        require_system_demo_admin(self.env)
        if self.state != "reset":
            raise UserError(_("Run Reset Preview and Execute Safe Reset before rebuild."))
        if not self.safety_acknowledged or not self.generation_enabled:
            raise UserError(_("NON-PRODUCTION safety enablement is required for rebuild."))
        if self.compatibility_status != "compatible":
            raise UserError(_("Refresh Source Compatibility and obtain PASS before rebuild."))

        # Re-check the same whole-path compatibility and operator readiness immediately
        # before reusing retained masters. No stale readiness is trusted after reset.
        readiness_action = self.action_validate_readiness()
        if self.readiness_status != "ready":
            return readiness_action
        return self._generate_selected_profile(self.profile)

    def _related_action(self, name, model, domain):
        return {"type":"ir.actions.act_window","name":name,"res_model":model,"view_mode":"list,form",
                "domain":domain,"context":{"create":False}}

    def action_open_runs(self):
        self.ensure_one()
        return self._related_action(_("Runs"),"onehr.demo.run",[("scenario_id","=",self.id)])

    def action_open_checkpoints(self):
        self.ensure_one()
        return self._related_action(_("Checkpoints"),"onehr.demo.checkpoint",[("scenario_id","=",self.id)])

    def action_open_references(self):
        self.ensure_one()
        return self._related_action(_("References"),"onehr.demo.reference",[("scenario_id","=",self.id)])

    def action_open_logs(self):
        self.ensure_one()
        return self._related_action(_("Logs"),"onehr.demo.log",[("scenario_id","=",self.id)])

    def action_open_generators(self):
        self.ensure_one()
        return self._related_action(_("Generator Registry"),"onehr.demo.generator",[])

    def action_open_latest_run(self):
        self.ensure_one()
        if not self.latest_run_id:
            raise UserError(_("No Demo Run exists yet."))
        return {"type":"ir.actions.act_window","name":self.latest_run_id.display_name,
                "res_model":"onehr.demo.run","res_id":self.latest_run_id.id,
                "view_mode":"form","target":"current"}

    def action_open_failed_checkpoint(self):
        self.ensure_one()
        if not self.current_failed_checkpoint_id:
            raise UserError(_("No failed checkpoint exists."))
        return {"type":"ir.actions.act_window","name":self.current_failed_checkpoint_id.generator_key,
                "res_model":"onehr.demo.checkpoint","res_id":self.current_failed_checkpoint_id.id,
                "view_mode":"form","target":"current"}

    def _notification(self, title, message, level, sticky=False, reload_form=False):
        """Return an operator notification with optional Control Center resynchronization.

        Lifecycle actions persist state server-side. Odoo does not automatically re-read the
        current form record after an object action that returns ``display_notification``.
        When a lifecycle action changes button/statusbar-driving fields, request a client
        reload after the notification so the visible Control Center is the same state that
        the server has committed.
        """
        params = {
            "title": title,
            "message": message,
            "type": level,
            "sticky": sticky,
        }
        if reload_form:
            params["next"] = {"type": "ir.actions.client", "tag": "reload"}
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": params,
        }


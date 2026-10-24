
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .authority_helpers import require_hrbp, require_talent_manager


class OneHRTalentPoolIntegrationServices(models.Model):
    _inherit = "onehr.talent.pool"

    def action_refresh_external_scores(self):
        """Refresh optional source evidence under the caller's normal source authority.

        This addon never sudo-bypasses Appraisal or Learning security. A Talent user who
        is not authorized in a source addon receives that source addon's normal denial.
        """
        require_hrbp(self)
        refreshed = 0
        for talent in self:
            values = {}

            if self.env.registry.get("onehr.appraisal.form"):
                Appraisal = self.env["onehr.appraisal.form"]
                forms = Appraisal.search(
                    [
                        ("employee_id", "=", talent.employee_id.id),
                        ("company_id", "=", talent.company_id.id),
                        ("state", "=", "closed"),
                    ],
                    order="closed_at desc, id desc",
                    limit=1,
                )
                if forms:
                    payload = forms.onehr_career_feedback_payload()[0]
                    values.update(
                        {
                            "performance_score": payload.get("performance_score") or 0.0,
                            "potential_score": payload.get("potential_score") or 0.0,
                            "appraisal_cycle_code": payload.get("cycle_code") or False,
                            "appraisal_reference": forms.name,
                            "strengths": payload.get("strengths") or talent.strengths,
                            "development_needs": (
                                payload.get("improvement_areas")
                                or talent.development_needs
                            ),
                        }
                    )

            if self.env.registry.get("onehr.learning.enrollment"):
                Enrollment = self.env["onehr.learning.enrollment"]
                enrollments = Enrollment.search(
                    [
                        ("employee_id", "=", talent.employee_id.id),
                        ("company_id", "=", talent.company_id.id),
                        ("state", "in", ("passed", "certified")),
                    ]
                )
                all_learning = Enrollment.search_count(
                    [
                        ("employee_id", "=", talent.employee_id.id),
                        ("company_id", "=", talent.company_id.id),
                        ("state", "not in", ("cancelled", "rejected")),
                    ]
                )
                values["learning_score"] = (
                    len(enrollments) * 100.0 / all_learning
                    if all_learning
                    else talent.learning_score
                )
                if enrollments:
                    values["learning_evidence_reference"] = ", ".join(
                        enrollments[:5].mapped("name")
                    )

            if values:
                values["source_refreshed_at"] = fields.Datetime.now()
                talent.write(values)
                refreshed += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("OneHR Career & Succession"),
                "message": _("%s talent record(s) refreshed from available source evidence.") % refreshed,
                "type": "success",
                "sticky": False,
            },
        }

    def onehr_talent_bi_payload(self):
        require_talent_manager(self)
        self.check_access("read")
        return [
            {
                "talent_id": record.id,
                "reference": record.name,
                "company_id": record.company_id.id,
                "employee_number": record.employee_number,
                "employee_id": record.employee_id.id,
                "pool_code": record.pool_code,
                "target_position_id": record.target_position_id.id or False,
                "state": record.state,
                "high_potential": record.high_potential,
                "performance_score": record.performance_score,
                "potential_score": record.potential_score,
                "competency_score": record.competency_score,
                "learning_score": record.learning_score,
                "readiness_score": record.readiness_score,
                "readiness_level": record.readiness_level,
                "nine_box_position": record.nine_box_position,
                "retention_risk": record.retention_risk,
            }
            for record in self
        ]

    @api.model
    def onehr_career_kpi_snapshot(self, company=None):
        require_talent_manager(self)
        company = company or self.env.company

        talents = self.search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "active"),
            ]
        )
        plans = self.env["onehr.succession.plan"].search(
            [
                ("company_id", "=", company.id),
                ("state", "=", "active"),
            ]
        )
        covered = plans.filtered(lambda plan: plan.coverage_percent >= 100.0)

        return {
            "company_id": company.id,
            "active_talent_count": len(talents),
            "high_potential_count": len(talents.filtered("high_potential")),
            "succession_plan_count": len(plans),
            "succession_coverage_percent": (
                len(covered) * 100.0 / len(plans) if plans else 0.0
            ),
            "average_bench_strength": (
                sum(plans.mapped("bench_strength")) / len(plans) if plans else 0.0
            ),
            "average_readiness": (
                sum(talents.mapped("readiness_score")) / len(talents)
                if talents
                else 0.0
            ),
        }

    @api.model
    def onehr_employee_career_payload(self, employee):
        """Portal/self-service payload exposing only the caller's own career facts."""
        employee.ensure_one()
        employee.check_access("read")
        if employee.user_id != self.env.user:
            raise AccessError(
                _("Employees may request only their own Career & Succession payload.")
            )

        talents = self.search(
            [
                ("employee_user_id", "=", self.env.user.id),
                ("company_id", "in", self.env.companies.ids),
                ("state", "in", ("approved", "active", "inactive")),
            ]
        )
        return [
            {
                "reference": record.name,
                "pool": record.pool_code,
                "target_position": record.target_position_name,
                "state": record.state,
                "readiness_level": record.readiness_level,
                "readiness_score": record.readiness_score,
                "career_aspiration": record.career_aspiration or "",
            }
            for record in talents
        ]

    @api.model
    def onehr_ingest_talent_assessment(self, payload):
        """Authenticated model-service boundary for future onehr_integrations_api."""
        require_talent_manager(self)
        if not isinstance(payload, dict):
            raise ValidationError(_("Talent assessment payload must be an object."))

        employee_number = (payload.get("employee_number") or "").strip()
        pool_code = (payload.get("pool_code") or "HIPOT").strip()
        if not employee_number:
            raise ValidationError(_("employee_number is required."))

        employee = self.env["hr.employee"].search(
            [
                ("onehr_employee_number", "=", employee_number),
                ("company_id", "in", self.env.companies.ids),
            ],
            limit=2,
        )
        if len(employee) != 1:
            raise ValidationError(
                _("Talent assessment must resolve to exactly one employee.")
            )

        talent = self.search(
            [
                ("employee_id", "=", employee.id),
                ("company_id", "=", employee.company_id.id),
                ("pool_code", "=", pool_code),
            ],
            limit=1,
        )
        values = {
            "performance_score": payload.get("performance_score", 0.0),
            "potential_score": payload.get("potential_score", 0.0),
            "competency_score": payload.get("competency_score", 0.0),
            "learning_score": payload.get("learning_score", 0.0),
            "high_potential": bool(payload.get("high_potential")),
            "assessment_notes": payload.get("assessment_notes") or "",
        }
        if talent:
            talent.write(values)
        else:
            values.update(
                {
                    "employee_id": employee.id,
                    "company_id": employee.company_id.id,
                    "pool_code": pool_code,
                }
            )
            talent = self.create(values)

        return {
            "talent_id": talent.id,
            "reference": talent.name,
            "state": talent.state,
            "readiness_score": talent.readiness_score,
        }


class OneHRCompetencyIntegrationServices(models.Model):
    _inherit = "onehr.competency"

    def onehr_competency_bi_payload(self):
        require_talent_manager(self)
        self.check_access("read")
        return [
            {
                "competency_id": record.id,
                "code": record.code,
                "name": record.name,
                "category": record.category,
                "level_min": record.level_min,
                "level_max": record.level_max,
                "company_id": record.company_id.id,
                "active": record.active,
            }
            for record in self
        ]



from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError

from .authority_helpers import require_jd_approver


class OneHRJobDescriptionIntegrationServices(models.Model):
    _inherit = "onehr.jd"

    @api.model
    def _onehr_find_published_jd(self, *, position=None, position_code=None):
        domain = [
            ("active", "=", True),
            ("is_template", "=", False),
            ("current_version_id", "!=", False),
            ("company_id", "in", self.env.companies.ids),
        ]
        if position:
            position.ensure_one()
            domain.append(("position_id", "=", position.id))
        elif position_code:
            domain.append(("position_code", "=", position_code))
        else:
            raise ValidationError(_("Position or position_code is required."))

        jd = self.search(domain, limit=1)
        if not jd:
            return self.browse()
        jd.check_access("read")
        return jd

    def onehr_jd_export_payload(self):
        self.check_access("read")
        payloads = []
        for jd in self:
            version = jd.current_version_id
            if not version:
                continue
            payloads.append(
                {
                    "jd_id": jd.id,
                    "jd_reference": jd.code,
                    "title": jd.name,
                    "company_id": jd.company_id.id,
                    "position_code": jd.position_code,
                    "position_name": jd.position_name,
                    "job_name": jd.job_name,
                    "job_family": jd.job_family_name,
                    "department": jd.department_name,
                    "grade": jd.grade_name,
                    "version": version.version_no,
                    "effective_from": version.effective_from,
                    "review_due_date": version.review_due_date,
                    "purpose": version.purpose or "",
                    "key_responsibilities": version.key_responsibilities or "",
                    "kpi_expectations": version.kpi_expectations or "",
                    "kpi_codes": version.kpi_codes or "",
                    "competency_requirements": version.competency_requirements or "",
                    "competency_codes": version.competency_codes or "",
                    "qualification_requirements": version.qualification_requirements or "",
                    "education_requirements": version.education_requirements or "",
                    "experience_requirements": version.experience_requirements or "",
                    "skills_requirements": version.skills_requirements or "",
                    "authority_scope": version.authority_scope or "",
                    "accountability": version.accountability or "",
                    "reporting_relationships": version.reporting_relationships or "",
                    "working_conditions": version.working_conditions or "",
                    "hse_risk_level": version.hse_risk_level,
                    "hse_risks": version.hse_risks or "",
                    "hse_controls": version.hse_controls or "",
                    "fingerprint": version.content_fingerprint,
                }
            )
        return payloads

    @api.model
    def onehr_jd_recruitment_payload(self, *, position=None, position_code=None):
        jd = self._onehr_find_published_jd(
            position=position,
            position_code=position_code,
        )
        if not jd:
            return {}
        payload = jd.onehr_jd_export_payload()[0]
        return {
            "jd_reference": payload["jd_reference"],
            "position_code": payload["position_code"],
            "position_name": payload["position_name"],
            "purpose": payload["purpose"],
            "key_responsibilities": payload["key_responsibilities"],
            "qualification_requirements": payload["qualification_requirements"],
            "education_requirements": payload["education_requirements"],
            "experience_requirements": payload["experience_requirements"],
            "skills_requirements": payload["skills_requirements"],
            "hse_risk_level": payload["hse_risk_level"],
        }

    @api.model
    def onehr_jd_appraisal_payload(self, *, position=None, position_code=None):
        jd = self._onehr_find_published_jd(
            position=position,
            position_code=position_code,
        )
        if not jd:
            return {}
        payload = jd.onehr_jd_export_payload()[0]
        return {
            "jd_reference": payload["jd_reference"],
            "position_code": payload["position_code"],
            "version": payload["version"],
            "kpi_codes": payload["kpi_codes"],
            "kpi_expectations": payload["kpi_expectations"],
            "competency_codes": payload["competency_codes"],
            "competency_requirements": payload["competency_requirements"],
        }

    @api.model
    def onehr_jd_portal_payload(self, *, position=None, position_code=None):
        """Safe published-content contract; route/session ownership stays downstream."""
        jd = self._onehr_find_published_jd(
            position=position,
            position_code=position_code,
        )
        if not jd:
            return {}
        payload = jd.onehr_jd_export_payload()[0]
        allowed = (
            "jd_reference",
            "title",
            "position_code",
            "position_name",
            "job_name",
            "job_family",
            "department",
            "grade",
            "version",
            "effective_from",
            "review_due_date",
            "purpose",
            "key_responsibilities",
            "kpi_expectations",
            "competency_requirements",
            "qualification_requirements",
            "education_requirements",
            "experience_requirements",
            "skills_requirements",
            "authority_scope",
            "reporting_relationships",
            "working_conditions",
            "hse_risk_level",
            "hse_risks",
            "hse_controls",
        )
        return {key: payload[key] for key in allowed}

    @api.model
    def onehr_jd_api_payload(self, jd_reference):
        """Model service for a future onehr_integrations_api adapter; no HTTP/auth ownership."""
        if not jd_reference:
            raise ValidationError(_("jd_reference is required."))
        jd = self.search(
            [
                ("code", "=", jd_reference),
                ("active", "=", True),
                ("current_version_id", "!=", False),
                ("company_id", "in", self.env.companies.ids),
            ],
            limit=1,
        )
        if not jd:
            return {}
        jd.check_access("read")
        return jd.onehr_jd_export_payload()[0]

    @api.model
    def onehr_jd_kpi_snapshot(self, company=None):
        require_jd_approver(self)
        company = company or self.env.company
        if company.id not in self.env.companies.ids:
            raise AccessError(_("Company is outside your allowed company scope."))

        Position = self.env["onehr.position"]
        positions = Position.search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
                ("status", "not in", ("closed",)),
            ]
        )
        jds = self.search(
            [
                ("company_id", "=", company.id),
                ("is_template", "=", False),
                ("active", "=", True),
            ]
        )
        covered = jds.filtered(lambda jd: bool(jd.current_version_id))
        ages = covered.mapped("version_age_days")
        overdue = covered.filtered("review_overdue")

        return {
            "company_id": company.id,
            "active_position_count": len(positions),
            "position_jd_count": len(jds),
            "published_position_jd_count": len(covered),
            "coverage_percent": (
                len(covered) * 100.0 / len(positions)
                if positions
                else 100.0
            ),
            "average_version_age_days": (
                sum(ages) / len(ages) if ages else 0.0
            ),
            "overdue_review_count": len(overdue),
        }


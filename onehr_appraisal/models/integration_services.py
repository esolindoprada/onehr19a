from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError

from .authority_helpers import is_appraisal_hr, require_appraisal_hr, require_appraisal_manager_or_hr


class OneHRAppraisalIntegrationServices(models.Model):
    _inherit = "onehr.appraisal.form"

    def onehr_appraisal_result_payload(self):
        """HR/BI result contract; transport/authentication stay outside Appraisal."""
        require_appraisal_hr(self)
        self.check_access("read")
        return [
            {
                "appraisal_id": form.id,
                "reference": form.name,
                "cycle_code": form.cycle_id.code,
                "company_id": form.company_id.id,
                "employee_number": form.employee_number,
                "employee_id": form.employee_id.id,
                "department_id": form.department_id.id or False,
                "job_id": form.job_id.id or False,
                "state": form.state,
                "self_score": form.self_score,
                "manager_score": form.manager_score,
                "peer_score": form.peer_score,
                "overall_score": form.overall_score,
                "final_score": form.final_score,
                "final_rating": form.final_rating_label,
                "potential_score": form.potential_score,
                "nine_box_position": form.nine_box_position,
                "acknowledged": form.employee_acknowledged,
            }
            for form in self
        ]

    @api.model
    def onehr_appraisal_kpi_snapshot(self, company=None):
        require_appraisal_manager_or_hr(self)
        self.check_access("read")
        company = company or self.env.company
        forms = self.search([
            ("company_id", "=", company.id),
            ("state", "!=", "cancelled"),
        ])
        closed = forms.filtered(lambda form: form.state == "closed")
        rated = closed.filtered(lambda form: form.final_score > 0)
        return {
            "company_id": company.id,
            "appraisal_count": len(forms),
            "closed_count": len(closed),
            "completion_rate": len(closed) * 100.0 / len(forms) if forms else 0.0,
            "average_final_score": (
                sum(rated.mapped("final_score")) / len(rated) if rated else 0.0
            ),
            "rating_distribution": {
                key: len(closed.filtered(
                    lambda form, rating=key: form.final_rating_label == rating
                ))
                for key in ("below", "partial", "meets", "exceeds", "outstanding")
            },
        }

    @api.model
    def onehr_employee_appraisal_payload(self, employee):
        """Portal/self-service boundary under the caller's normal record access."""
        employee.ensure_one()
        domain = [
            ("company_id", "in", self.env.companies.ids),
        ]
        if is_appraisal_hr(self.env):
            domain.append(("employee_id", "=", employee.id))
        else:
            domain.append(("employee_user_id", "=", self.env.user.id))
        forms = self.search(domain, order="cycle_id desc, id desc")
        return [
            {
                "appraisal_id": form.id,
                "reference": form.name,
                "cycle_code": form.cycle_id.code,
                "employee_name": form.employee_name,
                "state": form.state,
                "overall_score": form.overall_score,
                "final_score": form.final_score,
                "final_rating": form.final_rating_label,
                "acknowledged": form.employee_acknowledged,
            }
            for form in forms
        ]

    def onehr_career_feedback_payload(self):
        """Career/Succession remains owner of competency/talent/succession masters."""
        require_appraisal_hr(self)
        self.check_access("read")
        return [
            {
                "employee_id": form.employee_id.id,
                "employee_number": form.employee_number,
                "cycle_code": form.cycle_id.code,
                "performance_score": form.final_score,
                "potential_score": form.potential_score,
                "nine_box_position": form.nine_box_position,
                "strengths": form.strengths or "",
                "improvement_areas": form.improvement_areas or "",
            }
            for form in self.filtered(lambda record: record.state == "closed")
        ]

    def onehr_discipline_feedback_payload(self):
        """Evidence-only contract; Appraisal never creates a discipline case."""
        self.check_access("read")
        if not is_appraisal_hr(self.env):
            raise AccessError(
                _("Only Appraisal HR may expose discipline-feedback evidence.")
            )
        return [
            {
                "employee_id": form.employee_id.id,
                "appraisal_reference": form.name,
                "cycle_code": form.cycle_id.code,
                "final_score": form.final_score,
                "final_rating": form.final_rating_label,
                "improvement_areas": form.improvement_areas or "",
            }
            for form in self.filtered(lambda record: record.state == "closed")
        ]

    @api.model
    def onehr_ingest_external_rating(self, payload):
        """Authenticated HR service boundary for future onehr_integrations_api."""
        require_appraisal_hr(self)
        if not isinstance(payload, dict):
            raise ValidationError(_("External rating payload must be an object."))

        reference = (payload.get("appraisal_reference") or "").strip()
        reviewer_number = (payload.get("reviewer_employee_number") or "").strip()
        rater_type = (payload.get("rater_type") or "").strip()
        item_code = (payload.get("item_code") or "").strip()
        if not all((reference, reviewer_number, rater_type, item_code)):
            raise ValidationError(
                _(
                    "appraisal_reference, reviewer_employee_number, "
                    "rater_type and item_code are required."
                )
            )
        if rater_type not in ("self", "manager", "peer"):
            raise ValidationError(_("External rater_type must be self, manager or peer."))

        form = self.search([
            ("name", "=", reference),
            ("company_id", "in", self.env.companies.ids),
        ], limit=2)
        reviewer = self.env["hr.employee"].search([
            ("onehr_employee_number", "=", reviewer_number),
            ("company_id", "in", self.env.companies.ids),
        ], limit=2)
        if len(form) != 1 or len(reviewer) != 1:
            raise ValidationError(
                _("External rating must resolve to exactly one form and reviewer.")
            )

        line = self.env["onehr.appraisal.score"].search([
            ("form_id", "=", form.id),
            ("item_code", "=", item_code),
            ("rater_type", "=", rater_type),
            ("reviewer_employee_id", "=", reviewer.id),
        ], limit=2)
        if len(line) != 1:
            raise ValidationError(
                _("External rating must resolve to exactly one score line.")
            )

        line.write({
            "rating": payload.get("rating") or 0.0,
            "comments": payload.get("comments") or "",
        })
        line.action_submit_rating()
        return {
            "appraisal_id": form.id,
            "score_line_id": line.id,
            "rating_state": line.rating_state,
        }


from collections import Counter
from datetime import date, datetime

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import (
    display_notification,
    is_legal,
    is_manager,
    open_record_action,
    require_hrbp,
    require_legal,
    require_manager,
)


class OneHRDisciplineCaseIntegration(models.Model):
    _inherit = "onehr.discipline.case"

    def action_refresh_appraisal_feedback(self):
        """Read accepted Appraisal evidence under the caller's own authority.

        The Appraisal addon remains owner of appraisal evidence. No sudo and no
        hard dependency are introduced. Appraisal HR authority is intentionally
        required by the source service when that addon is installed.
        """
        require_hrbp(self)
        if not self.env.registry.get("onehr.appraisal.form"):
            raise UserError(
                _("OneHR Appraisal is not installed; no appraisal evidence was changed.")
            )

        Appraisal = self.env["onehr.appraisal.form"]
        for case in self:
            forms = Appraisal.search(
                [
                    ("employee_id", "=", case.employee_id.id),
                    ("state", "=", "closed"),
                    ("company_id", "=", case.company_id.id),
                ],
                order="cycle_id desc, id desc",
                limit=1,
            )
            if not forms:
                raise UserError(
                    _("No closed Appraisal record is available for %s.")
                    % case.employee_name
                )
            payloads = forms.onehr_discipline_feedback_payload()
            payload = payloads[0] if payloads else {}
            case._write_action(
                {
                    "appraisal_reference": payload.get(
                        "appraisal_reference"
                    )
                    or False,
                    "appraisal_cycle_code": payload.get(
                        "cycle_code"
                    )
                    or False,
                    "appraisal_final_score": payload.get(
                        "final_score"
                    )
                    or 0.0,
                    "appraisal_final_rating": payload.get(
                        "final_rating"
                    )
                    or False,
                    "appraisal_improvement_areas": payload.get(
                        "improvement_areas"
                    )
                    or False,
                    "appraisal_refreshed_at": fields.Datetime.now(),
                }
            )
        return display_notification(
            _("Latest closed Appraisal evidence refreshed under source-module security.")
        )

    def action_open_policy_reference(self):
        require_hrbp(self)
        self.ensure_one()
        if not self.policy_reference:
            raise UserError(_("No Policy / Rule Reference is recorded."))
        if not self.env.registry.get("onehr.policy"):
            raise UserError(
                _("OneHR PnP is not installed; the soft policy reference is preserved as text.")
            )
        policies = self.env["onehr.policy"].search(
            [
                ("policy_code", "=", self.policy_reference),
                ("company_id", "=", self.company_id.id),
            ],
            order="version_no desc, id desc",
            limit=1,
        )
        if not policies:
            raise UserError(
                _("No accessible OneHR PnP policy matches this reference.")
            )
        return open_record_action(
            name=_("Related Policy"),
            res_model="onehr.policy",
            res_id=policies.id,
        )

    def action_queue_hearing_notice(self):
        require_hrbp(self)
        self.ensure_one()
        if self.state not in ("hearing", "decision"):
            raise UserError(
                _("Hearing notice can be queued only from Hearing/Decision.")
            )
        if not self.hearing_scheduled_at:
            raise UserError(_("Hearing Scheduled At is required."))
        if not self.employee_id.work_email:
            raise UserError(
                _("The employee has no work email for the hearing notice.")
            )
        template = self.env.ref(
            "onehr_discipline.mail_template_discipline_hearing_notice"
        )
        template.send_mail(self.id, force_send=False)
        return display_notification(
            _("Hearing notice queued for email delivery.")
        )

    @api.model
    def onehr_discipline_kpi_snapshot(
        self,
        company=None,
        date_from=None,
        date_to=None,
    ):
        """Analytics/API-ready aggregate. No dashboard persistence is owned here."""
        require_manager(self)
        company = company or self.env.company
        if company not in self.env.companies:
            raise AccessError(
                _("Company is outside your allowed company scope.")
            )

        domain = [("company_id", "=", company.id)]
        if date_from and date_to:
            if fields.Date.to_date(date_to) < fields.Date.to_date(date_from):
                raise ValidationError(
                    _("Analytics date_to cannot be earlier than date_from.")
                )
        if date_from:
            date_from = fields.Date.to_date(date_from)
            domain.append(
                (
                    "reported_at",
                    ">=",
                    datetime.combine(
                        date_from,
                        datetime.min.time(),
                    ),
                )
            )
        if date_to:
            date_to = fields.Date.to_date(date_to)
            domain.append(
                (
                    "reported_at",
                    "<=",
                    datetime.combine(
                        date_to,
                        datetime.max.time(),
                    ),
                )
            )

        cases = self.search(domain)
        closed = cases.filtered(
            lambda case: case.state == "closed"
        )
        repeat_cases = closed.filtered("repeat_offense")
        category_counts = Counter(cases.mapped("violation_category"))
        state_counts = Counter(cases.mapped("state"))
        resolution_values = closed.filtered(
            lambda case: case.resolution_days > 0
        ).mapped("resolution_days")

        sanctions = self.env["onehr.discipline.sanction"].search(
            [
                ("case_id", "in", cases.ids),
                ("state", "in", ["approved", "executed"]),
            ]
        )
        sanction_counts = Counter(sanctions.mapped("sanction_type"))

        return {
            "company_id": company.id,
            "case_count": len(cases),
            "open_case_count": len(
                cases.filtered(
                    lambda case: case.state
                    not in ("closed", "cancelled")
                )
            ),
            "closed_case_count": len(closed),
            "sla_overdue_count": len(
                cases.filtered("sla_overdue")
            ),
            "repeat_offense_rate": (
                len(repeat_cases) * 100.0 / len(closed)
                if closed
                else 0.0
            ),
            "average_resolution_days": (
                sum(resolution_values) / len(resolution_values)
                if resolution_values
                else 0.0
            ),
            "violation_trend": dict(category_counts),
            "case_state_distribution": dict(state_counts),
            "sanction_type_distribution": dict(sanction_counts),
        }

    @api.model
    def onehr_discipline_case_audit_payload(self, reference):
        """Minimum-necessary audit export service under strict Discipline access."""
        require_legal(self)
        case = self.search(
            [
                ("reference", "=", reference),
                ("company_id", "in", self.env.companies.ids),
            ],
            limit=2,
        )
        if len(case) != 1:
            raise ValidationError(
                _("Case reference must resolve to exactly one accessible record.")
            )
        return {
            "reference": case.reference,
            "employee_number": case.employee_number,
            "employee_name": case.employee_name,
            "department": case.department_name,
            "job": case.job_name,
            "incident_date": case.incident_date,
            "reported_at": case.reported_at,
            "source_type": case.source_type,
            "violation_category": case.violation_category,
            "severity": case.severity,
            "violation_weight": case.violation_weight,
            "state": case.state,
            "evidence_assessment": case.evidence_assessment,
            "final_disposition": case.final_disposition,
            "appeal_state": case.appeal_state,
            "closed_at": case.closed_at,
            "resolution_days": case.resolution_days,
            "sanctions": [
                {
                    "reference": sanction.reference,
                    "sanction_type": sanction.sanction_type,
                    "state": sanction.state,
                    "decision_date": sanction.decision_date,
                    "approved_at": sanction.approved_at,
                    "executed_at": sanction.executed_at,
                    "payroll_execution_state": (
                        sanction.payroll_execution_state
                    ),
                }
                for sanction in case.sanction_ids
            ],
        }

    @api.model
    def onehr_discipline_document_payload(self, reference):
        """Soft OneHR Document handoff payload; no document record is created here."""
        require_legal(self)
        case = self.search(
            [
                ("reference", "=", reference),
                ("company_id", "in", self.env.companies.ids),
            ],
            limit=2,
        )
        if len(case) != 1:
            raise ValidationError(
                _("Case reference must resolve to exactly one accessible record.")
            )
        return {
            "source_model": case._name,
            "source_res_id": case.id,
            "reference": case.reference,
            "title": f"Discipline Case — {case.reference}",
            "company_id": case.company_id.id,
            "employee_id": case.employee_id.id,
            "employee_number": case.employee_number,
            "retention_until": case.retention_until,
            "sensitivity": "restricted",
            "keywords": [
                "discipline",
                case.violation_category,
                case.severity,
            ],
        }


class OneHRDisciplineSanctionIntegration(models.Model):
    _inherit = "onehr.discipline.sanction"

    def action_queue_decision_notice(self):
        require_legal(self)
        self.ensure_one()
        if self.state != "executed":
            raise UserError(
                _("Decision notice can be queued only after execution/issuance.")
            )
        if not self.employee_id.work_email:
            raise UserError(
                _("The employee has no work email for the decision notice.")
            )
        template = self.env.ref(
            "onehr_discipline.mail_template_discipline_decision_notice"
        )
        template.send_mail(self.id, force_send=False)
        return display_notification(
            _("Disciplinary decision notice queued for email delivery.")
        )

    @api.model
    def onehr_record_document_archive(
        self,
        sanction_reference,
        document_reference,
    ):
        """Record an owning Document adapter's reference only; no Document mutation."""
        require_legal(self)
        if not document_reference:
            raise ValidationError(
                _("document_reference is required.")
            )
        sanction = self.search(
            [
                ("reference", "=", sanction_reference),
                ("company_id", "in", self.env.companies.ids),
            ],
            limit=2,
        )
        if len(sanction) != 1:
            raise ValidationError(
                _("Sanction reference must resolve to exactly one accessible record.")
            )
        if sanction.state != "executed":
            raise UserError(
                _("Document archive evidence may be linked only after sanction execution.")
            )
        sanction._write_action(
            {"document_archive_reference": document_reference}
        )
        return True

    @api.model
    def onehr_discipline_payroll_payload(
        self,
        period_start,
        period_end,
        company=None,
    ):
        """Downstream Payroll Bridge adapter contract.

        Returns only approved/executed discipline-owned requests. It does not
        mutate payroll, payslips, work entries or accounting.
        """
        require_legal(self)
        company = company or self.env.company
        if company not in self.env.companies:
            raise AccessError(
                _("Company is outside your allowed company scope.")
            )
        if not period_start or not period_end:
            raise ValidationError(
                _("Payroll period_start and period_end are required.")
            )
        period_start = fields.Date.to_date(period_start)
        period_end = fields.Date.to_date(period_end)
        if period_end < period_start:
            raise ValidationError(
                _("Payroll period end cannot be earlier than period start.")
            )

        sanctions = self.search(
            [
                ("company_id", "=", company.id),
                ("sanction_type", "=", "payroll_deduction"),
                ("state", "=", "executed"),
                ("payroll_period_date", ">=", period_start),
                ("payroll_period_date", "<=", period_end),
            ]
        )
        return [
            {
                "sanction_reference": sanction.reference,
                "case_reference": sanction.case_reference,
                "employee_id": sanction.employee_id.id,
                "employee_number": sanction.employee_number,
                "amount": sanction.payroll_deduction_amount,
                "currency_id": sanction.currency_id.id,
                "period_date": sanction.payroll_period_date,
                "execution_state": sanction.payroll_execution_state,
            }
            for sanction in sanctions
        ]

    @api.model
    def onehr_discipline_contract_payload(self, employee, company=None):
        """Soft Employment Contract handoff for probation/termination review."""
        require_legal(self)
        company = company or self.env.company
        if company not in self.env.companies:
            raise AccessError(
                _("Company is outside your allowed company scope.")
            )
        if not employee or employee.company_id != company:
            raise ValidationError(
                _("Employee must belong to the requested company.")
            )
        sanctions = self.search(
            [
                ("company_id", "=", company.id),
                ("employee_id", "=", employee.id),
                ("state", "=", "executed"),
                ("contract_action", "!=", "none"),
            ],
            order="decision_date desc, id desc",
        )
        return [
            {
                "sanction_reference": sanction.reference,
                "case_reference": sanction.case_reference,
                "contract_action": sanction.contract_action,
                "contract_reference": sanction.contract_reference,
                "sanction_type": sanction.sanction_type,
                "probation_start_date": sanction.probation_start_date,
                "probation_end_date": sanction.probation_end_date,
                "probation_conditions": sanction.probation_conditions or "",
                "decision_date": sanction.decision_date,
            }
            for sanction in sanctions
        ]


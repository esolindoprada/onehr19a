
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .authority_helpers import require_sop_approver


class OneHRSOPIntegrationServices(models.Model):
    _inherit = "onehr.sop"

    @api.model
    def onehr_sop_portal_payload(self, sop_code):
        """Portal-safe current SOP payload.

        Portal routes, authentication and session ownership remain downstream.
        Normal SOP record rules enforce that the caller is in the published audience.
        """
        if not sop_code:
            raise ValidationError(_("sop_code is required."))

        sop = self.search(
            [
                ("code", "=", sop_code),
                ("active", "=", True),
                ("current_version_id", "!=", False),
                ("company_id", "in", self.env.companies.ids),
            ],
            limit=1,
        )
        if not sop:
            return {}

        sop.check_access("read")
        version = sop.current_version_id
        version.check_access("read")
        own_ack = version.ack_ids.filtered(
            lambda ack: ack.employee_user_id == self.env.user
        )[:1]

        return {
            "sop_id": sop.id,
            "sop_reference": sop.code,
            "title": sop.name,
            "version_id": version.id,
            "version": version.version_no,
            "effective_from": version.effective_from,
            "review_due_date": version.review_due_date,
            "purpose": version.purpose or "",
            "scope": version.scope or "",
            "definitions": version.definitions or "",
            "roles_responsibilities": version.roles_responsibilities or "",
            "procedure_steps": version.procedure_steps or "",
            "controls": version.controls or "",
            "records_evidence": version.records_evidence or "",
            "training_requirements": version.training_requirements or "",
            "safety_notes": version.safety_notes or "",
            "references": version.references or "",
            "ack_id": own_ack.id if own_ack else False,
            "ack_state": own_ack.state if own_ack else False,
            "acknowledged_at": own_ack.acknowledged_at if own_ack else False,
        }

    @api.model
    def onehr_sop_ack_status(self, *, employee_number=None, sop_code=None):
        """API-ready model service; HTTP auth/tokens remain onehr_integrations_api."""
        domain = [
            ("company_id", "in", self.env.companies.ids),
        ]

        if employee_number:
            if not self.env.user.has_group("onehr_sop.group_onehr_sop_approver"):
                raise AccessError(
                    _("Querying another employee's SOP status requires SOP Approver authority.")
                )
            domain.append(("employee_number", "=", employee_number))
        else:
            domain.append(("employee_user_id", "=", self.env.user.id))

        if sop_code:
            domain.append(("sop_id.code", "=", sop_code))

        acknowledgements = self.env["onehr.sop.ack"].search(domain)
        return [
            {
                "sop_reference": ack.sop_id.code,
                "sop_title": ack.sop_id.name,
                "version": ack.version_id.version_no,
                "employee_number": ack.employee_number,
                "state": ack.state,
                "published_at": ack.published_at,
                "acknowledged_at": ack.acknowledged_at,
                "source": ack.acknowledgement_source,
            }
            for ack in acknowledgements
        ]

    @api.model
    def onehr_sop_kpi_snapshot(self, company=None):
        require_sop_approver(self)
        company = company or self.env.company
        if company.id not in self.env.companies.ids:
            raise AccessError(_("Company is outside your allowed company scope."))

        sops = self.search(
            [
                ("company_id", "=", company.id),
                ("active", "=", True),
                ("current_version_id", "!=", False),
            ]
        )
        total_audience = sum(sops.mapped("current_ack_count"))
        total_done = sum(sops.mapped("current_acknowledged_count"))
        published = len(sops)
        overdue = len(sops.filtered("review_overdue"))
        days_90 = [
            value
            for value in sops.mapped("days_to_90_ack")
            if value > 0
        ]

        return {
            "company_id": company.id,
            "published_sop_count": published,
            "audience_count": total_audience,
            "acknowledged_count": total_done,
            "acknowledgement_rate": (
                total_done * 100.0 / total_audience
                if total_audience
                else 100.0
            ),
            "review_overdue_count": overdue,
            "average_days_to_90_ack": (
                sum(days_90) / len(days_90)
                if days_90
                else 0.0
            ),
        }


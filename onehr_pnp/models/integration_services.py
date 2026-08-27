from odoo import _, api, models
from odoo.exceptions import AccessError, ValidationError

from .authority_helpers import require_pnp_compliance


class OneHRPnPIntegrationServices(models.Model):
    _inherit = "onehr.policy"

    @api.model
    def onehr_policy_portal_payload(self, policy_code):
        """Employee-facing policy payload under normal PnP record rules.

        Portal routing, sessions and authentication remain downstream ownership.
        """
        if not policy_code:
            raise ValidationError(_("policy_code is required."))

        policy = self.search(
            [
                ("policy_code", "=", policy_code),
                ("is_current", "=", True),
                ("state", "in", ["published", "review"]),
                ("company_id", "in", self.env.companies.ids),
            ],
            order="version_no desc, id desc",
            limit=1,
        )
        if not policy:
            return {}

        policy.check_access("read")
        own_ack = policy.ack_ids.filtered(
            lambda ack: ack.employee_user_id == self.env.user
        )[:1]
        if not own_ack:
            raise AccessError(
                _("The current user is not in this policy publication audience.")
            )

        own_evidence = policy.evidence_ids.filtered(
            lambda evidence: evidence.employee_user_id == self.env.user
        )
        return {
            "policy_id": policy.id,
            "policy_reference": policy.policy_code,
            "version": policy.version_no,
            "title": policy.name,
            "policy_type": policy.policy_type,
            "effective_from": policy.effective_from,
            "review_due_date": policy.review_due_date,
            "state": policy.state,
            "purpose": policy.purpose or "",
            "scope": policy.scope or "",
            "policy_statement": policy.policy_statement or "",
            "responsibilities": policy.responsibilities or "",
            "controls": policy.controls or "",
            "exceptions": policy.exceptions or "",
            "references": policy.references or "",
            "related_sop_references": policy.related_sop_references or "",
            "ack_id": own_ack.id,
            "ack_state": own_ack.state,
            "ack_due_date": own_ack.due_date,
            "acknowledged_at": own_ack.acknowledged_at,
            "evidence_required": policy.evidence_required,
            "evidence": [
                {
                    "id": evidence.id,
                    "title": evidence.title,
                    "evidence_type": evidence.evidence_type,
                    "state": evidence.state,
                    "submitted_at": evidence.submitted_at,
                    "verified_at": evidence.verified_at,
                    "due_date": evidence.due_date,
                }
                for evidence in own_evidence
            ],
        }

    @api.model
    def onehr_pnp_ack_status(self, *, policy_code=None, employee_number=None):
        """API-ready model service; HTTP/token ownership stays downstream."""
        domain = [("company_id", "in", self.env.companies.ids)]

        if employee_number:
            require_pnp_compliance(self)
            domain.append(("employee_number", "=", employee_number))
        else:
            domain.append(("employee_user_id", "=", self.env.user.id))

        if policy_code:
            domain.append(("policy_code", "=", policy_code))

        acknowledgements = self.env["onehr.policy.ack"].search(domain)
        return [
            {
                "policy_reference": ack.policy_code,
                "policy_title": ack.policy_title,
                "version": ack.policy_version,
                "employee_number": ack.employee_number
                if employee_number
                else False,
                "state": ack.state,
                "due_date": ack.due_date,
                "published_at": ack.published_at,
                "acknowledged_at": ack.acknowledged_at,
                "acknowledgement_source": ack.acknowledgement_source,
                "verified_evidence_count": ack.verified_evidence_count,
            }
            for ack in acknowledgements
        ]

    @api.model
    def onehr_pnp_submit_evidence(self, payload):
        """Portal/API-ready evidence submission using the caller's own assignment."""
        if not isinstance(payload, dict):
            raise ValidationError(_("Evidence payload must be an object."))

        policy_code = (payload.get("policy_code") or "").strip()
        title = (payload.get("title") or "").strip()
        evidence_type = (payload.get("evidence_type") or "note").strip()
        if not policy_code or not title:
            raise ValidationError(_("policy_code and title are required."))

        ack = self.env["onehr.policy.ack"].search(
            [
                ("policy_code", "=", policy_code),
                ("employee_user_id", "=", self.env.user.id),
                ("policy_id.is_current", "=", True),
                ("policy_id.state", "in", ["published", "review"]),
                ("company_id", "in", self.env.companies.ids),
            ],
            limit=1,
        )
        if not ack:
            raise AccessError(
                _("No current policy assignment was found for the current user.")
            )

        allowed_types = {"attachment", "url", "note"}
        if evidence_type not in allowed_types:
            raise ValidationError(
                _("Portal/API employee evidence type must be attachment, url or note.")
            )

        attachment_ids = payload.get("attachment_ids") or []
        attachments = self.env["ir.attachment"].browse(attachment_ids).exists()
        if len(attachments) != len(set(attachment_ids)):
            raise ValidationError(_("One or more evidence attachments do not exist."))
        attachments.check_access("read")

        evidence = self.env["onehr.policy.evidence"].create(
            {
                "policy_id": ack.policy_id.id,
                "ack_id": ack.id,
                "evidence_type": evidence_type,
                "title": title,
                "evidence_note": payload.get("note") or "",
                "reference_url": payload.get("url") or "",
                "attachment_ids": [(6, 0, attachments.ids)],
            }
        )
        evidence.action_submit()
        return {
            "evidence_id": evidence.id,
            "state": evidence.state,
            "submitted_at": evidence.submitted_at,
        }

    @api.model
    def onehr_pnp_compliance_snapshot(self, company=None):
        """Analytics-ready policy compliance metrics; dashboard ownership remains downstream."""
        require_pnp_compliance(self)
        company = company or self.env.company
        if company not in self.env.companies:
            raise AccessError(_("Company is outside your allowed company scope."))

        policies = self.search(
            [
                ("company_id", "=", company.id),
                ("is_current", "=", True),
                ("state", "in", ["published", "review"]),
            ]
        )
        audience = sum(policies.mapped("audience_count"))
        acknowledged = sum(policies.mapped("acknowledged_count"))
        verified_evidence = sum(policies.mapped("verified_evidence_count"))
        overdue_reviews = len(policies.filtered("review_overdue"))
        ack_rates = policies.filtered(
            lambda policy: policy.audience_count > 0
        ).mapped("acknowledgement_rate")
        evidence_rates = policies.filtered(
            lambda policy: policy.audience_count > 0
        ).mapped("evidence_coverage_rate")

        return {
            "company_id": company.id,
            "current_policy_count": len(policies),
            "review_overdue_count": overdue_reviews,
            "audience_count": audience,
            "acknowledged_count": acknowledged,
            "verified_evidence_count": verified_evidence,
            "average_acknowledgement_rate": (
                sum(ack_rates) / len(ack_rates) if ack_rates else 0.0
            ),
            "average_evidence_coverage_rate": (
                sum(evidence_rates) / len(evidence_rates)
                if evidence_rates
                else 0.0
            ),
        }

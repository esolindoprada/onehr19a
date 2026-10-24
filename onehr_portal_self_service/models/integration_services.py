
from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .authority_helpers import require_portal_hr


EXPECTED_INTEGRATION_ERRORS = (AccessError, UserError, ValidationError)


class OneHRPortalRequestIntegrationServices(models.Model):
    _inherit = "onehr.portal.request"

    def _record_integration_result(self, *, status, model=False, res_id=False, reference=False, message=False):
        self.ensure_one()
        values = {
            "integration_status": status,
            "integration_model": model or False,
            "integration_res_id": res_id or 0,
            "integration_reference": reference or False,
            "integration_message": message or False,
            "integration_last_attempt_at": fields.Datetime.now(),
            "integration_last_attempt_by_id": self.env.user.id,
        }
        self._write_governed(values)
        return True

    def _dispatch_integration(self, *, raise_on_error=False):
        """Execute only the explicitly configured service hand-off.

        This addon never bypasses another addon's ACL, record rules or authority helper.
        Expected authorization/configuration failures are retained as request evidence so
        an appropriately authorized operator can retry. Unexpected Python/runtime defects
        are deliberately not swallowed.
        """
        self.ensure_one()
        require_portal_hr(self)

        if self.service_kind == "generic":
            self._record_integration_result(
                status="not_applicable",
                message=_("Generic HR service has no automatic downstream transaction."),
            )
            return True

        try:
            if self.service_kind == "profile_change":
                result = self._dispatch_profile_change()
            elif self.service_kind == "timeoff":
                result = self._dispatch_timeoff()
            elif self.service_kind == "learning":
                result = self._dispatch_learning()
            elif self.service_kind == "document":
                result = self._dispatch_document()
            else:
                raise ValidationError(_("Unsupported self-service integration kind: %s") % self.service_kind)
        except EXPECTED_INTEGRATION_ERRORS as exc:
            self._record_integration_result(status="error", message=str(exc))
            if raise_on_error:
                raise
            return False

        self._record_integration_result(
            status="success",
            model=result.get("model"),
            res_id=result.get("res_id"),
            reference=result.get("reference"),
            message=result.get("message"),
        )
        self.message_post(
            body=_("Downstream service completed: %s", result.get("reference") or result.get("message") or self.service_kind),
            subtype_xmlid="mail.mt_note",
        )
        return True

    def _dispatch_profile_change(self):
        self.ensure_one()
        requested = dict(self.profile_change_json or {})
        if not requested:
            raise ValidationError(_("No profile changes are present on this request."))

        allowed = {
            item.strip()
            for item in (self.type_id.profile_allowed_fields or "").split(",")
            if item.strip()
        }
        if not allowed:
            raise ValidationError(_("This Request Type has no approved profile fields configured."))

        unknown = set(requested) - allowed
        if unknown:
            raise AccessError(_("Profile fields are outside the approved self-service whitelist: %s") % ", ".join(sorted(unknown)))

        model_fields = self.employee_id._fields
        missing = set(requested) - set(model_fields)
        if missing:
            raise ValidationError(_("Configured profile fields do not exist on hr.employee: %s") % ", ".join(sorted(missing)))

        protected_relational = {
            name
            for name in requested
            if model_fields[name].type in {"many2one", "one2many", "many2many", "binary"}
        }
        if protected_relational:
            raise AccessError(_("Relational/binary profile fields are not accepted through this self-service request: %s") % ", ".join(sorted(protected_relational)))

        self.employee_id.write(requested)
        return {
            "model": "hr.employee",
            "res_id": self.employee_id.id,
            "reference": self.employee_name,
            "message": _("Approved profile changes were applied to the canonical employee record."),
        }

    def _dispatch_timeoff(self):
        self.ensure_one()
        if not self.env.registry.get("onehr.leave.request"):
            raise UserError(_("OneHR Time Off is not installed."))
        if not all((self.leave_type_code, self.requested_date_from, self.requested_date_to)):
            raise ValidationError(_("Leave Type Code, Requested From and Requested To are required."))

        LeaveType = self.env["onehr.leave.type"]
        leave_type = LeaveType.search(
            [
                ("code", "=", self.leave_type_code.strip().upper()),
                ("company_id", "=", self.company_id.id),
                ("state", "=", "active"),
                ("active", "=", True),
            ],
            limit=2,
        )
        if len(leave_type) != 1:
            raise ValidationError(_("Leave Type Code must resolve to exactly one active OneHR leave policy."))

        LeaveRequest = self.env["onehr.leave.request"]
        leave = LeaveRequest.create(
            {
                "employee_id": self.employee_id.id,
                "leave_type_id": leave_type.id,
                "date_from": self.requested_date_from,
                "date_to": self.requested_date_to,
                "reason": self.description,
            }
        )
        leave.action_submit_for_approval()
        return {
            "model": "onehr.leave.request",
            "res_id": leave.id,
            "reference": leave.name,
            "message": _("OneHR Time Off request created and submitted under Time Off authority."),
        }

    def _dispatch_learning(self):
        self.ensure_one()
        if not self.env.registry.get("onehr.learning.enrollment"):
            raise UserError(_("OneHR Learning is not installed."))
        if not self.learning_session_reference:
            raise ValidationError(_("Learning Session Reference is required."))
        if not self.employee_number:
            raise ValidationError(_("The employee requires a OneHR Employee Number."))

        result = self.env["onehr.learning.enrollment"].onehr_external_enroll(
            {
                "external_system": "ONEHR_PORTAL_SELF_SERVICE",
                "external_reference": self.name,
                "employee_number": self.employee_number,
                "session_reference": self.learning_session_reference,
                "request_reason": self.description,
                "submit_for_approval": True,
            }
        )
        enrollment = self.env["onehr.learning.enrollment"].browse(result["enrollment_id"]).exists()
        return {
            "model": "onehr.learning.enrollment",
            "res_id": enrollment.id,
            "reference": enrollment.name if enrollment else str(result["enrollment_id"]),
            "message": _("OneHR Learning enrollment created through the accepted service contract."),
        }

    def _dispatch_document(self):
        self.ensure_one()
        if not self.env.registry.get("onehr.document"):
            raise UserError(_("OneHR Document is not installed."))
        if not self.document_category_code:
            raise ValidationError(_("Document Category Code is required."))
        if not self.attachment_ids:
            raise ValidationError(_("At least one supporting attachment is required."))

        category = self.env["onehr.document.category"].search(
            [
                ("code", "=", self.document_category_code.strip().upper()),
                ("active", "=", True),
                "|",
                ("company_id", "=", self.company_id.id),
                ("company_id", "=", False),
            ],
            limit=2,
        )
        if len(category) != 1:
            raise ValidationError(_("Document Category Code must resolve to exactly one active category."))

        document = self.env["onehr.document"].create(
            {
                "name": self.document_title or self.subject,
                "category_id": category.id,
                "company_id": self.company_id.id,
                "employee_id": self.employee_id.id,
                "responsible_user_id": self.env.user.id,
                "valid_from": fields.Date.context_today(self),
            }
        )
        attachment = self.attachment_ids[:1]
        version = self.env["onehr.document.version"].create(
            {
                "document_id": document.id,
                "file_data": attachment.datas,
                "file_name": attachment.name,
                "mimetype": attachment.mimetype,
                "effective_from": fields.Date.context_today(self),
            }
        )
        return {
            "model": "onehr.document",
            "res_id": document.id,
            "reference": document.document_number,
            "message": _("OneHR Document header and Draft version created from the submitted attachment."),
        }

    @api.model
    def onehr_my_hr_dashboard_payload(self):
        """Portal dashboard payload under the caller's normal access only.

        Soft integrations are best-effort and security-preserving: a card is omitted when
        its owner addon is absent or the current actor does not have the owner's ACL/rules.
        """
        employee = self.env.user.employee_id
        if not employee:
            return {"employee": {}, "request_metrics": {}, "integrations": {}}

        requests = self.search([("employee_user_id", "=", self.env.user.id)])
        metrics = {
            "total": len(requests),
            "open": len(requests.filtered(lambda rec: rec.state not in FINAL_STATES)),
            "awaiting_manager": len(requests.filtered(lambda rec: rec.state == "manager_review")),
            "awaiting_hr": len(requests.filtered(lambda rec: rec.state == "hr_review")),
            "overdue": len(requests.filtered("is_sla_overdue")),
            "done": len(requests.filtered(lambda rec: rec.state == "done")),
        }
        integrations = {}

        def safe_call(key, callback):
            try:
                integrations[key] = callback()
            except EXPECTED_INTEGRATION_ERRORS:
                integrations[key] = []

        if self.env.registry.get("onehr.appraisal.form"):
            safe_call(
                "appraisals",
                lambda: self.env["onehr.appraisal.form"].onehr_employee_appraisal_payload(employee),
            )
        if self.env.registry.get("onehr.learning.enrollment"):
            safe_call(
                "learning",
                lambda: self.env["onehr.learning.enrollment"].onehr_participant_portal_payload(employee),
            )
        if self.env.registry.get("onehr.talent.pool"):
            safe_call(
                "career",
                lambda: self.env["onehr.talent.pool"].onehr_employee_career_payload(employee),
            )
        if self.env.registry.get("onehr.payroll.import"):
            def payroll_payload():
                records = self.env["onehr.payroll.import"].search(
                    [
                        ("employee_id", "=", employee.id),
                        ("company_id", "in", self.env.companies.ids),
                        ("is_current_revision", "=", True),
                        ("state", "in", ("validated", "reconciled")),
                    ],
                    order="period_end desc, id desc",
                    limit=12,
                )
                return [record.onehr_portal_payslip_payload() for record in records]
            safe_call("payslips", payroll_payload)
        if self.env.registry.get("onehr.policy"):
            safe_call("policy_acknowledgements", lambda: self.env["onehr.policy"].onehr_pnp_ack_status())
        if self.env.registry.get("onehr.sop"):
            safe_call("sop_acknowledgements", lambda: self.env["onehr.sop"].onehr_sop_ack_status())
        if self.env.registry.get("onehr.jd") and self.env.user.onehr_portal_position_code:
            safe_call(
                "job_description",
                lambda: self.env["onehr.jd"].onehr_jd_portal_payload(
                    position_code=self.env.user.onehr_portal_position_code
                ),
            )

        return {
            "employee": self.env.user.onehr_portal_profile_payload(),
            "request_metrics": metrics,
            "integrations": integrations,
        }


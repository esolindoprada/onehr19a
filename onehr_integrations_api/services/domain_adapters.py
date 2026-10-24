from odoo import fields

from .errors import AuthorizationError, CapabilityUnavailable, PayloadError


class DomainAdapters:
    """Thin adapters only: business ownership remains in each installed OneHR addon."""

    def __init__(self, runtime, identity):
        self.runtime = runtime
        self.identity = identity
        self.env = runtime.env

    def _model(self, model_name):
        if not self.env.registry.get(model_name):
            raise CapabilityUnavailable(model_name)
        return self.runtime.service_model(self.identity, model_name)

    def _require_fields(self, payload, names):
        missing = [name for name in names if payload.get(name) in (None, "")]
        if missing:
            raise PayloadError("Missing required payload fields.", {"missing": missing})

    def health(self):
        optional_models = [
            "hr.employee", "hr.attendance", "hr.applicant", "onehr.leave.request",
            "onehr.approval.request", "onehr.esign.transaction", "onehr.learning.enrollment",
            "onehr.appraisal.form", "onehr.talent.pool", "onehr.payroll.export",
            "onehr.policy", "onehr.sop", "onehr.jd", "onehr.portal.request",
        ]
        return {
            "status": "ok",
            "api_version": "v1",
            "company_id": self.identity.company.id,
            "company_name": self.identity.company.name,
            "service_user_id": self.identity.service_user.id,
            "capabilities": {name: bool(self.env.registry.get(name)) for name in optional_models},
        }

    def employees(self, query):
        Employee = self._model("hr.employee")
        domain = [("company_id", "=", self.identity.company.id), ("active", "=", True)]
        domain += self.runtime.branch_domain(self.identity, Employee)
        if query.get("department_id"):
            domain.append(("department_id", "=", int(query["department_id"])))
        if query.get("search"):
            domain.append(("name", "ilike", str(query["search"])[:100]))
        limit = max(1, min(int(query.get("limit") or 50), 200))
        offset = max(0, int(query.get("offset") or 0))
        employees = Employee.search(domain, limit=limit, offset=offset, order="name, id")
        rows = []
        for employee in employees:
            row = {
                "id": employee.id,
                "name": employee.name,
                "company_id": employee.company_id.id,
                "department_id": employee.department_id.id or False,
                "department": employee.department_id.name or False,
                "job_id": employee.job_id.id or False,
                "job": employee.job_id.name or False,
            }
            if "onehr_employee_number" in Employee._fields:
                row["employee_number"] = employee.onehr_employee_number or False
            if "work_email" in Employee._fields:
                row["work_email"] = employee.work_email or False
            rows.append(row)
        return {"count": len(rows), "limit": limit, "offset": offset, "items": rows}

    def attendance(self, payload):
        Attendance = self._model("hr.attendance")
        method = getattr(Attendance, "onehr_ingest_interval", None)
        if not method:
            raise CapabilityUnavailable("hr.attendance.onehr_ingest_interval")
        values = dict(payload)
        values.setdefault("source_channel", "api")
        values.setdefault("source_system", "ONEHR_API")
        record = method(values)
        return {"attendance_ids": record.ids, "idempotent": True}

    def recruitment_applicant(self, payload):
        Applicant = self._model("hr.applicant")
        self._require_fields(payload, ("name",))
        values = {}
        mapping = {
            "name": "name",
            "candidate_name": "partner_name",
            "email": "email_from",
            "phone": "partner_phone",
            "mobile": "partner_mobile",
            "job_id": "job_id",
        }
        for source, target in mapping.items():
            if source in payload and target in Applicant._fields:
                values[target] = payload[source]
        if "company_id" in Applicant._fields:
            values["company_id"] = self.identity.company.id
        record = Applicant.create(values)
        return {"applicant_id": record.id, "reference": record.display_name}

    def timeoff_request(self, payload):
        Request = self._model("onehr.leave.request")
        self._require_fields(payload, ("employee_id", "leave_type_id", "date_from", "date_to"))
        allowed = {
            "employee_id", "leave_type_id", "date_from", "date_to", "reason",
            "half_day", "half_day_period", "request_unit",
        }
        values = {key: value for key, value in payload.items() if key in allowed and key in Request._fields}
        if "company_id" in Request._fields:
            values["company_id"] = self.identity.company.id
        request_record = Request.create(values)
        submit = getattr(request_record, "action_submit_for_approval", None)
        if payload.get("submit_for_approval", True) and submit:
            submit()
        return {"request_id": request_record.id, "reference": request_record.display_name, "state": getattr(request_record, "state", False)}

    def approval_event(self, payload):
        Approval = self._model("onehr.approval.request")
        self._require_fields(payload, ("request_id", "decision"))
        record = Approval.browse(int(payload["request_id"])).exists()
        if not record:
            raise PayloadError("Approval request was not found.")
        if "company_id" in Approval._fields and record.company_id != self.identity.company:
            raise AuthorizationError("Approval request is outside the API key company.")
        decision = payload["decision"]
        if "decision_comment" in Approval._fields and payload.get("comment") is not None:
            record.write({"decision_comment": payload.get("comment")})
        if decision == "approve":
            record.action_approve()
        elif decision == "reject":
            record.action_reject()
        else:
            raise PayloadError("decision must be 'approve' or 'reject'.")
        return {"request_id": record.id, "state": getattr(record, "state", False)}

    def document_esign_status(self, payload):
        Esign = self._model("onehr.esign.transaction")
        self._require_fields(payload, ("transaction_id", "state"))
        transaction = Esign.browse(int(payload["transaction_id"])).exists()
        if not transaction:
            raise PayloadError("e-Sign transaction was not found.")
        if "company_id" in Esign._fields and transaction.company_id != self.identity.company:
            raise AuthorizationError("e-Sign transaction is outside the API key company.")
        method = getattr(transaction, "apply_provider_status", None)
        if not method:
            raise CapabilityUnavailable("onehr.esign.transaction.apply_provider_status")
        method(
            state=payload["state"],
            provider_reference=payload.get("provider_reference"),
            note=payload.get("note"),
        )
        return {"transaction_id": transaction.id, "state": getattr(transaction, "state", False)}

    def learning_result(self, payload):
        Enrollment = self._model("onehr.learning.enrollment")
        method = getattr(Enrollment, "onehr_ingest_external_result", None)
        if not method:
            raise CapabilityUnavailable("onehr.learning.enrollment.onehr_ingest_external_result")
        return method(payload)

    def learning_enrollment(self, payload):
        Enrollment = self._model("onehr.learning.enrollment")
        method = getattr(Enrollment, "onehr_external_enroll", None)
        if not method:
            raise CapabilityUnavailable("onehr.learning.enrollment.onehr_external_enroll")
        return method(payload)

    def appraisal_rating(self, payload):
        Appraisal = self._model("onehr.appraisal.form")
        method = getattr(Appraisal, "onehr_ingest_external_rating", None)
        if not method:
            raise CapabilityUnavailable("onehr.appraisal.form.onehr_ingest_external_rating")
        return method(payload)

    def career_assessment(self, payload):
        Talent = self._model("onehr.talent.pool")
        method = getattr(Talent, "onehr_ingest_talent_assessment", None)
        if not method:
            raise CapabilityUnavailable("onehr.talent.pool.onehr_ingest_talent_assessment")
        return method(payload)

    def payroll_export(self, export_id):
        Export = self._model("onehr.payroll.export")
        record = Export.browse(int(export_id)).exists()
        if not record:
            raise PayloadError("Payroll export was not found.")
        if "company_id" in Export._fields and record.company_id != self.identity.company:
            raise AuthorizationError("Payroll export is outside the API key company.")
        method = getattr(record, "onehr_payroll_export_payload", None)
        if not method:
            raise CapabilityUnavailable("onehr.payroll.export.onehr_payroll_export_payload")
        return method()

    def payroll_result(self, payload):
        Import = self._model("onehr.payroll.import")
        method = getattr(Import, "onehr_ingest_payroll_result", None)
        if not method:
            raise CapabilityUnavailable("onehr.payroll.import.onehr_ingest_payroll_result")
        return method(payload)

    def policy_acknowledgements(self, query):
        Policy = self._model("onehr.policy")
        method = getattr(Policy, "onehr_pnp_ack_status", None)
        if not method:
            raise CapabilityUnavailable("onehr.policy.onehr_pnp_ack_status")
        return method(policy_code=query.get("policy_code"), employee_number=query.get("employee_number"))

    def policy_evidence(self, payload):
        Policy = self._model("onehr.policy")
        method = getattr(Policy, "onehr_pnp_submit_evidence", None)
        if not method:
            raise CapabilityUnavailable("onehr.policy.onehr_pnp_submit_evidence")
        return method(payload)

    def sop_acknowledgements(self, query):
        Sop = self._model("onehr.sop")
        method = getattr(Sop, "onehr_sop_ack_status", None)
        if not method:
            raise CapabilityUnavailable("onehr.sop.onehr_sop_ack_status")
        return method(employee_number=query.get("employee_number"), sop_code=query.get("sop_code"))

    def job_description(self, reference):
        JD = self._model("onehr.jd")
        method = getattr(JD, "onehr_jd_api_payload", None)
        if not method:
            raise CapabilityUnavailable("onehr.jd.onehr_jd_api_payload")
        return method(reference)

    def portal_my_hr(self):
        Portal = self._model("onehr.portal.request")
        method = getattr(Portal, "onehr_my_hr_dashboard_payload", None)
        if not method:
            raise CapabilityUnavailable("onehr.portal.request.onehr_my_hr_dashboard_payload")
        return method()

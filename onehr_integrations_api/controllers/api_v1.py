import json
import time

from odoo import http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import Response, request

from ..services.domain_adapters import DomainAdapters
from ..services.errors import ApiError
from ..services.openapi import OPENAPI_DOCUMENT
from ..services.runtime import ApiRuntime


class OneHRApiV1Controller(http.Controller):
    """Explicit REST transport. Every business call runs as the configured service user."""

    def _json_response(self, payload, status=200, runtime=None):
        headers = [("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store")]
        origin = request.httprequest.headers.get("Origin")
        if origin and runtime:
            configured = [item.strip() for item in (runtime.params.get_param("onehr_integrations_api.cors_origins", "") or "").split(",") if item.strip()]
            if "*" in configured:
                headers.append(("Access-Control-Allow-Origin", "*"))
            elif origin in configured:
                headers.extend([("Access-Control-Allow-Origin", origin), ("Vary", "Origin")])
        return Response(json.dumps(payload, ensure_ascii=False, default=str), status=status, headers=headers)

    def _outcome_for_status(self, status):
        if 200 <= status < 300:
            return "success"
        if status == 401:
            return "auth_error"
        if status == 403:
            return "forbidden"
        if status == 429:
            return "rate_limited"
        if status < 500:
            return "client_error"
        return "server_error"

    def _execute(self, scope_code, handler, *, mutating=False, event_code=None):
        started = time.monotonic()
        runtime = ApiRuntime(request.env, request.httprequest)
        raw_body = request.httprequest.get_data(cache=True) or b""
        identity = None
        payload = {}
        response_payload = {}
        status = 200
        error = None
        try:
            identity = runtime.authenticate(scope_code, raw_body, require_request_id=mutating)
            payload = runtime.parse_json_body(raw_body) if raw_body else {}
            adapter = DomainAdapters(runtime, identity)
            result = handler(adapter, payload, request.httprequest.args.to_dict())
            response_payload = {
                "ok": True,
                "request_id": identity.request_id or False,
                "data": result,
            }
            if event_code and mutating:
                dedupe_key = identity.request_id or runtime.response_hash(result)
                request.env["onehr.webhook"].emit_event(
                    event_code,
                    {
                        "event": event_code,
                        "request_id": identity.request_id,
                        "company_id": identity.company.id,
                        "data": result,
                    },
                    identity.company,
                    dedupe_key,
                )
        except ApiError as exc:
            error = exc
            status = exc.status
            response_payload = {
                "ok": False,
                "error": {"code": exc.code, "message": exc.message, "details": exc.details},
            }
        except AccessError as exc:
            error = exc
            status = 403
            response_payload = {"ok": False, "error": {"code": "domain_access_denied", "message": "The configured service identity is not authorized for this business operation.", "details": {}}}
        except (ValidationError, UserError, ValueError) as exc:
            error = exc
            status = 400
            response_payload = {"ok": False, "error": {"code": "business_validation_error", "message": str(exc), "details": {}}}
        except Exception as exc:  # transport must return a stable schema; full error remains in server/audit evidence
            error = exc
            status = 500
            response_payload = {"ok": False, "error": {"code": "internal_error", "message": "The integration request could not be completed.", "details": {}}}

        latency_ms = (time.monotonic() - started) * 1000.0
        # Authentication failures for unknown keys cannot be safely company-attributed.
        # Known identities are always logged. Unknown failures remain in Odoo HTTP logs.
        if identity:
            try:
                runtime.create_log(
                    identity,
                    status=status,
                    outcome=self._outcome_for_status(status),
                    latency_ms=latency_ms,
                    raw_body=raw_body,
                    response=response_payload,
                    error=error,
                )
            except Exception:
                # Audit failure must not turn a successful business transaction into a replayed client retry.
                # Server logging remains available and runtime acceptance tests this condition explicitly.
                if 200 <= status < 300:
                    status = 500
                    response_payload = {"ok": False, "error": {"code": "audit_persistence_failed", "message": "The business operation completed but integration audit persistence failed; manual reconciliation is required.", "details": {}}}
        return self._json_response(response_payload, status=status, runtime=runtime)

    @http.route("/onehr/api/v1/<path:api_path>", type="http", auth="public", methods=["OPTIONS"], csrf=False, save_session=False)
    def cors_preflight(self, api_path, **kwargs):
        runtime = ApiRuntime(request.env, request.httprequest)
        origin = request.httprequest.headers.get("Origin")
        configured = [item.strip() for item in (runtime.params.get_param("onehr_integrations_api.cors_origins", "") or "").split(",") if item.strip()]
        headers = [
            ("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS"),
            ("Access-Control-Allow-Headers", "Content-Type, X-API-Key, X-Request-ID, X-Timestamp, X-Signature"),
            ("Access-Control-Max-Age", "600"),
        ]
        if origin and ("*" in configured or origin in configured):
            headers.append(("Access-Control-Allow-Origin", "*" if "*" in configured else origin))
            return Response("", status=204, headers=headers)
        return Response("", status=403, headers=headers)

    @http.route("/onehr/api/v1/health", type="http", auth="public", methods=["GET"], csrf=False, save_session=False)
    def health(self, **kwargs):
        return self._execute("system.health", lambda adapter, payload, query: adapter.health())

    @http.route("/onehr/api/v1/employees", type="http", auth="public", methods=["GET"], csrf=False, save_session=False)
    def employees(self, **kwargs):
        return self._execute("corehr.employee.read", lambda adapter, payload, query: adapter.employees(query))

    @http.route("/onehr/api/v1/attendance", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def attendance(self, **kwargs):
        return self._execute("attendance.write", lambda adapter, payload, query: adapter.attendance(payload), mutating=True, event_code="attendance.interval.received")

    @http.route("/onehr/api/v1/recruitment/applicants", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def recruitment_applicants(self, **kwargs):
        return self._execute("recruitment.applicant.write", lambda adapter, payload, query: adapter.recruitment_applicant(payload), mutating=True, event_code="recruitment.applicant.created")

    @http.route("/onehr/api/v1/timeoff/requests", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def timeoff_requests(self, **kwargs):
        return self._execute("timeoff.request.write", lambda adapter, payload, query: adapter.timeoff_request(payload), mutating=True, event_code="timeoff.request.created")

    @http.route("/onehr/api/v1/approvals/events", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def approval_events(self, **kwargs):
        return self._execute("workflow.approval.decide", lambda adapter, payload, query: adapter.approval_event(payload), mutating=True, event_code="workflow.approval.decided")

    @http.route("/onehr/api/v1/documents/esign/status", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def esign_status(self, **kwargs):
        return self._execute("document.esign.write", lambda adapter, payload, query: adapter.document_esign_status(payload), mutating=True, event_code="document.esign.status.changed")

    @http.route("/onehr/api/v1/learning/results", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def learning_results(self, **kwargs):
        return self._execute("learning.result.write", lambda adapter, payload, query: adapter.learning_result(payload), mutating=True, event_code="learning.result.received")

    @http.route("/onehr/api/v1/learning/enrollments", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def learning_enrollments(self, **kwargs):
        return self._execute("learning.enrollment.write", lambda adapter, payload, query: adapter.learning_enrollment(payload), mutating=True, event_code="learning.enrollment.created")

    @http.route("/onehr/api/v1/appraisals/ratings", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def appraisal_ratings(self, **kwargs):
        return self._execute("appraisal.rating.write", lambda adapter, payload, query: adapter.appraisal_rating(payload), mutating=True, event_code="appraisal.rating.received")

    @http.route("/onehr/api/v1/career/assessments", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def career_assessments(self, **kwargs):
        return self._execute("career.assessment.write", lambda adapter, payload, query: adapter.career_assessment(payload), mutating=True, event_code="career.assessment.received")

    @http.route("/onehr/api/v1/payroll/exports/<int:export_id>", type="http", auth="public", methods=["GET"], csrf=False, save_session=False)
    def payroll_export(self, export_id, **kwargs):
        return self._execute("payroll.export.read", lambda adapter, payload, query: adapter.payroll_export(export_id))

    @http.route("/onehr/api/v1/payroll/results", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def payroll_results(self, **kwargs):
        return self._execute("payroll.result.write", lambda adapter, payload, query: adapter.payroll_result(payload), mutating=True, event_code="payroll.result.received")

    @http.route("/onehr/api/v1/policies/acknowledgements", type="http", auth="public", methods=["GET"], csrf=False, save_session=False)
    def policy_acknowledgements(self, **kwargs):
        return self._execute("pnp.ack.read", lambda adapter, payload, query: adapter.policy_acknowledgements(query))

    @http.route("/onehr/api/v1/policies/evidence", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def policy_evidence(self, **kwargs):
        return self._execute("pnp.evidence.write", lambda adapter, payload, query: adapter.policy_evidence(payload), mutating=True, event_code="pnp.evidence.received")

    @http.route("/onehr/api/v1/sops/acknowledgements", type="http", auth="public", methods=["GET"], csrf=False, save_session=False)
    def sop_acknowledgements(self, **kwargs):
        return self._execute("sop.ack.read", lambda adapter, payload, query: adapter.sop_acknowledgements(query))

    @http.route("/onehr/api/v1/job-descriptions/<string:reference>", type="http", auth="public", methods=["GET"], csrf=False, save_session=False)
    def job_description(self, reference, **kwargs):
        return self._execute("jd.read", lambda adapter, payload, query: adapter.job_description(reference))

    @http.route("/onehr/api/v1/portal/my-hr", type="http", auth="public", methods=["GET"], csrf=False, save_session=False)
    def portal_my_hr(self, **kwargs):
        return self._execute("portal.myhr.read", lambda adapter, payload, query: adapter.portal_my_hr())

    @http.route(["/onehr/api/openapi.json", "/onehr/api/v1/openapi"], type="http", auth="public", methods=["GET"], csrf=False, save_session=False)
    def openapi_document(self, **kwargs):
        return self._execute("system.docs", lambda adapter, payload, query: OPENAPI_DOCUMENT)

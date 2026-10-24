import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import timedelta

from odoo import fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import Response, request

from ..services.domain_adapters import DomainAdapters
from ..services.errors import ApiError, PayloadError
from ..services.runtime import ApiRuntime


@dataclass(frozen=True)
class WebhookIdentity:
    webhook: object
    request_id: str

    @property
    def company(self):
        return self.webhook.company_id

    @property
    def service_user(self):
        return self.webhook.service_user_id

    @property
    def api_key(self):
        # DomainAdapters.branch_domain only reads branch_code; inbound allow-list
        # currently does not expose employee-list reads but keeping the shape explicit
        # prevents accidental company widening if it is reused later.
        return self.webhook


class OneHRInboundWebhookController(http.Controller):
    def _response(self, payload, status):
        return Response(
            json.dumps(payload, ensure_ascii=False, default=str),
            status=status,
            headers=[("Content-Type", "application/json; charset=utf-8"), ("Cache-Control", "no-store")],
        )

    def _verify(self, webhook, raw_body):
        request_id = (request.httprequest.headers.get("X-Request-ID") or "").strip()
        timestamp = (request.httprequest.headers.get("X-Timestamp") or "").strip()
        signature = (request.httprequest.headers.get("X-Signature") or "").strip()
        if not request_id or not timestamp or not signature:
            raise PayloadError("Inbound webhook requires X-Request-ID, X-Timestamp and X-Signature.")
        try:
            timestamp_value = int(timestamp)
        except ValueError as exc:
            raise PayloadError("X-Timestamp must be a Unix epoch integer.") from exc
        params = request.env["ir.config_parameter"].sudo()
        tolerance = int(params.get_param("onehr_integrations_api.hmac_tolerance_seconds", "300") or 300)
        if abs(int(time.time()) - timestamp_value) > max(30, min(tolerance, 3600)):
            raise PayloadError("Webhook timestamp is outside the allowed replay window.")
        expected = hmac.new(
            (webhook.secret or "").encode("utf-8"),
            (timestamp + "\n" + request_id + "\n" + hashlib.sha256(raw_body).hexdigest()).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        presented = signature[7:] if signature.lower().startswith("sha256=") else signature
        if not hmac.compare_digest(expected, presented.lower()):
            raise PayloadError("Invalid webhook HMAC signature.")
        if request.env["onehr.api.log"].sudo().search_count([("webhook_id", "=", webhook.id), ("request_id", "=", request_id)], limit=1):
            raise PayloadError("Webhook request ID has already been processed.")
        cutoff = fields.Datetime.now() - timedelta(minutes=1)
        count = request.env["onehr.api.log"].sudo().search_count([
            ("webhook_id", "=", webhook.id), ("direction", "=", "inbound"), ("event_at", ">=", cutoff),
        ])
        if count >= webhook.rate_limit_per_minute:
            raise ApiError(429, "rate_limited", "Inbound webhook rate limit exceeded.")
        return request_id

    def _dispatch(self, webhook, adapter, payload):
        handlers = {
            "attendance.interval": adapter.attendance,
            "document.esign.status": adapter.document_esign_status,
            "learning.result": adapter.learning_result,
            "appraisal.rating": adapter.appraisal_rating,
            "career.assessment": adapter.career_assessment,
            "payroll.result": adapter.payroll_result,
        }
        handler = handlers.get(webhook.event_code)
        if not handler:
            raise PayloadError("Inbound webhook event is not allow-listed.")
        return handler(payload)

    @http.route("/onehr/webhook/v1/<string:endpoint_key>", type="http", auth="public", methods=["POST"], csrf=False, save_session=False)
    def inbound_webhook(self, endpoint_key, **kwargs):
        started = time.monotonic()
        raw_body = request.httprequest.get_data(cache=True) or b""
        webhook = request.env["onehr.webhook"].sudo().search([
            ("endpoint_key", "=", endpoint_key),
            ("direction", "=", "inbound"),
            ("state", "=", "active"),
            ("active", "=", True),
        ], limit=1)
        if not webhook:
            return self._response({"ok": False, "error": {"code": "webhook_not_found", "message": "Inbound webhook endpoint is unavailable."}}, 404)

        status = 200
        error = None
        request_id = ""
        response_payload = {}
        try:
            request_id = self._verify(webhook, raw_body)
            runtime = ApiRuntime(request.env, request.httprequest)
            payload = runtime.parse_json_body(raw_body)
            identity = WebhookIdentity(webhook, request_id)
            adapter = DomainAdapters(runtime, identity)
            result = self._dispatch(webhook, adapter, payload)
            response_payload = {"ok": True, "request_id": request_id, "data": result}
        except ApiError as exc:
            error = exc
            status = exc.status
            response_payload = {"ok": False, "error": {"code": exc.code, "message": exc.message, "details": exc.details}}
        except AccessError as exc:
            error = exc
            status = 403
            response_payload = {"ok": False, "error": {"code": "domain_access_denied", "message": "Webhook service identity is not authorized for this domain operation."}}
        except (ValidationError, UserError, ValueError) as exc:
            error = exc
            status = 400
            response_payload = {"ok": False, "error": {"code": "business_validation_error", "message": str(exc)}}
        except Exception as exc:
            error = exc
            status = 500
            response_payload = {"ok": False, "error": {"code": "internal_error", "message": "Inbound webhook processing failed."}}

        try:
            request.env["onehr.api.log"].technical_create({
                "event_at": fields.Datetime.now(),
                "company_id": webhook.company_id.id,
                "webhook_id": webhook.id,
                "service_user_id": webhook.service_user_id.id,
                "direction": "inbound",
                "request_id": request_id or (request.httprequest.headers.get("X-Request-ID") or "")[:128],
                "inbound_replay_key": f"webhook:{webhook.id}:{request_id}" if request_id else False,
                "scope_code": webhook.event_code,
                "method": "POST",
                "path": request.httprequest.path[:512],
                "remote_ip": (request.httprequest.remote_addr or "")[:128],
                "user_agent": (request.httprequest.headers.get("User-Agent") or "")[:512],
                "http_status": status,
                "outcome": "success" if status < 300 else "rate_limited" if status == 429 else "forbidden" if status == 403 else "client_error" if status < 500 else "server_error",
                "latency_ms": (time.monotonic() - started) * 1000.0,
                "request_hash": hashlib.sha256(raw_body).hexdigest(),
                "response_hash": hashlib.sha256(json.dumps(response_payload, sort_keys=True, default=str).encode("utf-8")).hexdigest(),
                "error_class": error.__class__.__name__ if error else False,
                "error_message": str(error)[:4000] if error else False,
            })
        except Exception:
            if status < 300:
                status = 500
                response_payload = {"ok": False, "error": {"code": "audit_persistence_failed", "message": "Webhook domain operation completed but audit persistence failed; manual reconciliation is required."}}
        return self._response(response_payload, status)

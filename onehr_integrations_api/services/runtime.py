import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import timedelta

from odoo import fields

from .errors import AuthenticationError, AuthorizationError, PayloadError, RateLimitError, ReplayError

REDACT_KEYS = {
    "authorization", "x-api-key", "api_key", "apikey", "password", "secret",
    "token", "access_token", "refresh_token", "signature", "x-signature",
}


@dataclass(frozen=True)
class ApiIdentity:
    api_key: object
    raw_secret: str
    request_id: str
    scope_code: str

    @property
    def company(self):
        return self.api_key.company_id

    @property
    def service_user(self):
        return self.api_key.service_user_id


class ApiRuntime:
    """Public HTTP authentication/audit helper; never owns sibling business logic."""

    def __init__(self, env, httprequest):
        self.env = env
        self.httprequest = httprequest
        self.params = env["ir.config_parameter"].sudo()

    def api_enabled(self):
        return self.params.get_param("onehr_integrations_api.api_enabled", "True") not in ("False", "0", "false")

    def max_payload_bytes(self):
        kb = int(self.params.get_param("onehr_integrations_api.max_payload_kb", "1024") or 1024)
        return max(1, min(kb, 10240)) * 1024

    def parse_json_body(self, raw_body):
        if not raw_body:
            return {}
        if len(raw_body) > self.max_payload_bytes():
            raise PayloadError("JSON payload exceeds the configured maximum size.")
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise PayloadError("Request body must contain valid UTF-8 JSON.") from exc
        if not isinstance(payload, dict):
            raise PayloadError("Top-level JSON payload must be an object.")
        return payload

    def authenticate(self, scope_code, raw_body=b"", *, require_request_id=False):
        if not self.api_enabled():
            raise AuthenticationError("OneHR External API is disabled by system configuration.")

        presented_key = self.httprequest.headers.get("X-API-Key", "")
        key, raw_secret = self.env["onehr.api.key"].authenticate_presented_key(presented_key)
        if not key:
            raise AuthenticationError()

        request_id = (self.httprequest.headers.get("X-Request-ID") or "").strip()
        if require_request_id and not request_id:
            raise PayloadError("X-Request-ID is required for mutating requests.")
        if len(request_id) > 128:
            raise PayloadError("X-Request-ID is too long.")

        if scope_code not in key.scope_ids.filtered("active").mapped("code"):
            raise AuthorizationError()

        if request_id and self._is_replay(key, request_id):
            raise ReplayError()

        if key.hmac_required:
            self._verify_hmac(key, raw_secret, raw_body, request_id)

        self._check_rate_limit(key)
        key.technical_mark_used(self.httprequest.remote_addr)
        return ApiIdentity(key, raw_secret, request_id, scope_code)

    def _verify_hmac(self, key, raw_secret, raw_body, request_id):
        timestamp = (self.httprequest.headers.get("X-Timestamp") or "").strip()
        signature = (self.httprequest.headers.get("X-Signature") or "").strip()
        if not timestamp or not signature or not request_id:
            raise AuthenticationError("HMAC-protected requests require X-Timestamp, X-Request-ID and X-Signature.")
        try:
            timestamp_value = int(timestamp)
        except ValueError as exc:
            raise AuthenticationError("X-Timestamp must be a Unix epoch integer.") from exc

        tolerance = int(self.params.get_param("onehr_integrations_api.hmac_tolerance_seconds", "300") or 300)
        tolerance = max(30, min(tolerance, 3600))
        if abs(int(time.time()) - timestamp_value) > tolerance:
            raise AuthenticationError("Request timestamp is outside the allowed HMAC replay window.")

        body_hash = hashlib.sha256(raw_body or b"").hexdigest()
        canonical = "\n".join([
            timestamp,
            request_id,
            self.httprequest.method.upper(),
            self.httprequest.path,
            body_hash,
        ])
        expected = hmac.new(raw_secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()
        presented = signature[7:] if signature.lower().startswith("sha256=") else signature
        if not hmac.compare_digest(expected, presented.lower()):
            raise AuthenticationError("Invalid request HMAC signature.")

    def _is_replay(self, key, request_id):
        return bool(self.env["onehr.api.log"].sudo().search_count([
            ("api_key_id", "=", key.id),
            ("request_id", "=", request_id),
        ], limit=1))

    def _check_rate_limit(self, key):
        limit = key.rate_limit_per_minute or int(self.params.get_param("onehr_integrations_api.default_rate_limit", "60") or 60)
        limit = max(1, min(limit, 100_000))
        cutoff = fields.Datetime.now() - timedelta(minutes=1)
        count = self.env["onehr.api.log"].sudo().search_count([
            ("api_key_id", "=", key.id),
            ("event_at", ">=", cutoff),
            ("direction", "=", "inbound"),
        ])
        if count >= limit:
            raise RateLimitError()

    def service_model(self, identity, model_name):
        """Return a domain model under the configured least-privilege service user."""
        model = self.env[model_name].with_user(identity.service_user).with_company(identity.company)
        return model.with_context(allowed_company_ids=[identity.company.id])

    def branch_domain(self, identity, model, *, branch_field="branch_id"):
        branch_code = (identity.api_key.branch_code or "").strip()
        if not branch_code:
            return []
        if branch_field not in model._fields:
            raise AuthorizationError(
                "This API key is branch-scoped, but the domain model has no verifiable branch boundary. Access is denied rather than widened."
            )
        branch_model = model._fields[branch_field].comodel_name
        Branch = self.service_model(identity, branch_model)
        code_field = "code" if "code" in Branch._fields else "name"
        branch = Branch.search([(code_field, "=", branch_code)], limit=2)
        if len(branch) != 1:
            raise AuthorizationError("The API key branch scope could not be resolved uniquely.")
        return [(branch_field, "=", branch.id)]

    @staticmethod
    def body_hash(raw_body):
        return hashlib.sha256(raw_body or b"").hexdigest()

    @staticmethod
    def response_hash(payload):
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def sanitized_payload_text(self, payload):
        enabled = self.params.get_param("onehr_integrations_api.log_payloads", "False") in ("True", "1", "true")
        if not enabled:
            return False
        sanitized = self._redact(payload)
        return json.dumps(sanitized, ensure_ascii=False, sort_keys=True, default=str)[:20000]

    def _redact(self, value):
        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if str(key).lower() in REDACT_KEYS:
                    result[key] = "***REDACTED***"
                else:
                    result[key] = self._redact(item)
            return result
        if isinstance(value, list):
            return [self._redact(item) for item in value[:100]]
        return value

    def create_log(self, identity, *, status, outcome, latency_ms, raw_body=b"", response=None, error=None):
        key = identity.api_key if identity else self.env["onehr.api.key"]
        values = {
            "event_at": fields.Datetime.now(),
            "company_id": key.company_id.id if key else False,
            "api_key_id": key.id if key else False,
            "service_user_id": key.service_user_id.id if key else False,
            "direction": "inbound",
            "request_id": identity.request_id if identity else (self.httprequest.headers.get("X-Request-ID") or "")[:128],
            "scope_code": identity.scope_code if identity else False,
            "method": self.httprequest.method.upper(),
            "path": self.httprequest.path[:512],
            "remote_ip": (self.httprequest.remote_addr or "")[:128],
            "user_agent": (self.httprequest.headers.get("User-Agent") or "")[:512],
            "http_status": int(status),
            "outcome": outcome,
            "latency_ms": round(float(latency_ms), 3),
            "request_hash": self.body_hash(raw_body),
            "response_hash": self.response_hash(response or {}),
            "request_payload": self.sanitized_payload_text(self.parse_json_body(raw_body) if raw_body else {}),
            "response_payload": self.sanitized_payload_text(response or {}),
            "error_class": error.__class__.__name__ if error else False,
            "error_message": str(error)[:4000] if error else False,
        }
        return self.env["onehr.api.log"].technical_create(values)

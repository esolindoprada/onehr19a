import hashlib
import hmac
import ipaddress
import json
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from odoo import fields


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class WebhookDeliveryService:
    """Bounded outbound HTTP transport; it never mutates sibling business-domain models."""

    MAX_RESPONSE_BYTES = 256 * 1024

    def __init__(self, env):
        self.env = env
        self.params = env["ir.config_parameter"].sudo()

    def _allow_http(self):
        return self.params.get_param("onehr_integrations_api.webhook_allow_http", "False") in ("True", "1", "true")

    def _allow_private(self):
        return self.params.get_param("onehr_integrations_api.webhook_allow_private_targets", "False") in ("True", "1", "true")

    def validate_target(self, url):
        parsed = urlsplit((url or "").strip())
        if parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("Webhook URL must be a normal HTTP(S) URL without embedded credentials.")
        if parsed.scheme == "http" and not self._allow_http():
            raise ValueError("Plain HTTP webhook targets are disabled by system policy.")
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
        if not addresses:
            raise ValueError("Webhook target hostname did not resolve.")
        if not self._allow_private():
            for item in addresses:
                ip = ipaddress.ip_address(item[4][0])
                if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
                    raise ValueError("Webhook target resolves to a private/unsafe network address blocked by policy.")
        return True

    def deliver(self, queue):
        queue = queue.sudo()
        queue.ensure_one()
        if queue.state not in ("pending", "retry"):
            return False
        hook = queue.webhook_id.sudo()
        if hook.state != "active" or hook.direction != "outbound":
            queue.with_context(onehr_api_queue_controlled=True).write({
                "state": "dead_letter",
                "last_error_class": "WebhookInactive",
                "last_error_message": "Outbound webhook is not Active.",
                "retry_at": False,
            })
            return False

        started = time.monotonic()
        queue.with_context(onehr_api_queue_controlled=True).write({
            "state": "processing",
            "attempts": queue.attempts + 1,
            "last_attempt_at": fields.Datetime.now(),
        })
        raw_body = queue.payload_json.encode("utf-8")
        status = 0
        response_body = b""
        error = None
        try:
            self.validate_target(hook.target_url)
            timestamp = str(int(time.time()))
            signature = hmac.new(
                (hook.secret or "").encode("utf-8"),
                (timestamp + "\n" + queue.request_id + "\n" + hashlib.sha256(raw_body).hexdigest()).encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "OneHR-Webhook/1.0",
                "X-OneHR-Event": queue.event_code,
                "X-Request-ID": queue.request_id,
                "X-Timestamp": timestamp,
                "X-Signature": "sha256=" + signature,
            }
            request = Request(hook.target_url, data=raw_body, headers=headers, method="POST")
            opener = build_opener(_NoRedirectHandler())
            with opener.open(request, timeout=hook.timeout_seconds) as response:
                status = int(response.status)
                response_body = response.read(self.MAX_RESPONSE_BYTES + 1)
                if len(response_body) > self.MAX_RESPONSE_BYTES:
                    raise ValueError("Webhook response exceeded the bounded response size.")
            if status < 200 or status >= 300:
                raise ValueError(f"Webhook returned HTTP {status}.")
        except HTTPError as exc:
            status = int(exc.code or 0)
            error = exc
            try:
                response_body = exc.read(self.MAX_RESPONSE_BYTES)
            except Exception:
                response_body = b""
        except (URLError, OSError, ValueError) as exc:
            error = exc

        latency_ms = (time.monotonic() - started) * 1000.0
        response_hash = hashlib.sha256(response_body).hexdigest()
        if error is None and 200 <= status < 300:
            queue.with_context(onehr_api_queue_controlled=True).write({
                "state": "sent",
                "sent_at": fields.Datetime.now(),
                "retry_at": False,
                "last_http_status": status,
                "last_error_class": False,
                "last_error_message": False,
                "response_hash": response_hash,
            })
            hook.with_context(onehr_webhook_controlled=True).write({
                "last_success_at": fields.Datetime.now(),
                "last_http_status": status,
                "last_message": "Delivered",
            })
            outcome = "success"
        else:
            exhausted = queue.attempts >= queue.max_attempts
            queue.with_context(onehr_api_queue_controlled=True).write({
                "state": "dead_letter" if exhausted else "retry",
                "retry_at": False if exhausted else queue.next_retry_time(),
                "last_http_status": status,
                "last_error_class": error.__class__.__name__ if error else "HttpError",
                "last_error_message": str(error or f"HTTP {status}")[:4000],
                "response_hash": response_hash,
            })
            hook.with_context(onehr_webhook_controlled=True).write({
                "last_failure_at": fields.Datetime.now(),
                "last_http_status": status,
                "last_message": str(error or f"HTTP {status}")[:255],
            })
            outcome = "server_error"

        self.env["onehr.api.log"].technical_create({
            "event_at": fields.Datetime.now(),
            "company_id": queue.company_id.id,
            "webhook_id": hook.id,
            "direction": "outbound",
            "request_id": queue.request_id,
            "scope_code": queue.event_code,
            "method": "POST",
            "path": hook.target_url[:512],
            "http_status": status,
            "outcome": outcome,
            "latency_ms": latency_ms,
            "request_hash": queue.payload_hash,
            "response_hash": response_hash,
            "error_class": error.__class__.__name__ if error else False,
            "error_message": str(error)[:4000] if error else False,
            "queue_id": queue.id,
        })
        return error is None

import hashlib
import hmac
import time
from types import SimpleNamespace

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from ..services.errors import AuthorizationError, ReplayError
from ..services.runtime import ApiRuntime
from .common import OneHRApiCommon


@tagged("post_install", "-at_install", "onehr_integrations_api")
class TestCredentialsAndReplay(OneHRApiCommon):
    def fake_request(self, headers=None, method="GET", path="/onehr/api/v1/health"):
        return SimpleNamespace(headers=headers or {}, method=method, path=path, remote_addr="127.0.0.1")

    def test_09_api_key_plaintext_secret_is_not_persisted(self):
        key = self.make_key()
        raw = self.generated_raw_key(key)
        self.assertTrue(raw.startswith(f"onehr_{key.public_id}."))
        secret = raw.split(".", 1)[1]
        self.assertNotEqual(key.secret_hash, secret)
        self.assertNotIn(secret, key.secret_hash)

    def test_10_api_key_authentication_accepts_correct_key(self):
        key = self.make_key()
        raw = self.generated_raw_key(key)
        key.with_user(self.admin).action_activate()
        authenticated, presented_secret = self.env["onehr.api.key"].authenticate_presented_key(raw)
        self.assertEqual(authenticated, key)
        self.assertTrue(presented_secret)

    def test_11_wrong_secret_is_rejected(self):
        key = self.make_key()
        self.generated_raw_key(key)
        key.with_user(self.admin).action_activate()
        authenticated, secret = self.env["onehr.api.key"].authenticate_presented_key(f"onehr_{key.public_id}.wrong")
        self.assertFalse(authenticated)
        self.assertFalse(secret)

    def test_12_key_requires_scope_before_activation(self):
        key = self.env["onehr.api.key"].with_user(self.admin).create({
            "name": "No Scope", "company_id": self.company.id, "service_user_id": self.service_user.id,
        })
        self.generated_raw_key(key)
        with self.assertRaises(UserError):
            key.with_user(self.admin).action_activate()

    def test_13_hmac_signature_contract(self):
        scope = self.make_scope(code="test.hmac")
        key = self.make_key(scope)
        raw = self.generated_raw_key(key)
        key.with_user(self.admin).action_activate()
        secret = raw.split(".", 1)[1]
        request_id = f"req-{self._testMethodName}"
        timestamp = str(int(time.time()))
        body = b"{}"
        body_hash = hashlib.sha256(body).hexdigest()
        canonical = "\n".join([timestamp, request_id, "POST", "/onehr/api/v1/test", body_hash])
        signature = hmac.new(secret.encode(), canonical.encode(), hashlib.sha256).hexdigest()
        fake = self.fake_request({
            "X-API-Key": raw, "X-Request-ID": request_id,
            "X-Timestamp": timestamp, "X-Signature": "sha256=" + signature,
        }, method="POST", path="/onehr/api/v1/test")
        identity = ApiRuntime(self.env, fake).authenticate("test.hmac", body, require_request_id=True)
        self.assertEqual(identity.api_key, key)

    def test_14_scope_mismatch_is_forbidden(self):
        scope = self.make_scope(code="test.allowed")
        key = self.make_key(scope, hmac_required=False)
        raw = self.generated_raw_key(key)
        key.with_user(self.admin).action_activate()
        fake = self.fake_request({"X-API-Key": raw})
        with self.assertRaises(AuthorizationError):
            ApiRuntime(self.env, fake).authenticate("test.not.allowed")

    def test_15_replay_request_id_is_detected(self):
        scope = self.make_scope(code="test.replay")
        key = self.make_key(scope, hmac_required=False)
        raw = self.generated_raw_key(key)
        key.with_user(self.admin).action_activate()
        request_id = f"replay-{self._testMethodName}"
        self.env["onehr.api.log"].technical_create({
            "company_id": self.company.id, "api_key_id": key.id, "service_user_id": self.service_user.id,
            "direction": "inbound", "request_id": request_id, "scope_code": scope.code,
            "method": "POST", "path": "/test", "http_status": 200, "outcome": "success",
        })
        fake = self.fake_request({"X-API-Key": raw, "X-Request-ID": request_id}, method="POST", path="/test")
        with self.assertRaises(ReplayError):
            ApiRuntime(self.env, fake).authenticate(scope.code, b"{}", require_request_id=True)

    def test_16_revoked_key_cannot_be_reactivated(self):
        key = self.make_key()
        self.generated_raw_key(key)
        key.with_user(self.admin).action_activate()
        key.with_user(self.admin).action_revoke()
        with self.assertRaises(AccessError):
            key.with_user(self.admin).action_activate()

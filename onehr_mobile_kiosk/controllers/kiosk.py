from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request


class OneHRKioskController(http.Controller):
    """Authenticated kiosk shell + JSON-RPC services.

    The browser/device authenticates as its dedicated Odoo service user and must
    also present the device token.  This addon intentionally exposes no public
    attendance bypass; external third-party APIs remain owned by
    ``onehr_integrations_api``.
    """

    def _device(self, device_code):
        code = str(device_code or "").strip().upper()
        device = request.env["onehr.kiosk.device"].search(
            [("code", "=", code), ("active", "=", True)],
            limit=1,
        )
        if not device:
            raise AccessError(_("Kiosk device is unavailable in your security scope."))
        return device

    @http.route(
        "/onehr/kiosk/<string:device_code>",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=True,
    )
    def kiosk_page(self, device_code, **kwargs):
        device = self._device(device_code)
        # Page access is still server-authorized; token is entered only after render
        # so the raw token never appears in the URL or server access log.
        if (
            request.env.user != device.service_user_id
            and not request.env.user.has_group("onehr_mobile_kiosk.group_onehr_kiosk_admin")
        ):
            raise AccessError(_("The current user is not assigned to this kiosk device."))
        return request.render(
            "onehr_mobile_kiosk.kiosk_page",
            {
                "device": device,
                "device_code": device.code,
            },
        )

    @http.route(
        "/onehr/kiosk/api/bootstrap",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def kiosk_bootstrap(self, device_code, device_token, client_version=None):
        return self._device(device_code).kiosk_bootstrap(device_token, client_version)

    @http.route(
        "/onehr/kiosk/api/identify",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def kiosk_identify(self, device_code, device_token, identity):
        return self._device(device_code).kiosk_employee_snapshot(device_token, identity)

    @http.route(
        "/onehr/kiosk/api/punch",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def kiosk_punch(self, device_code, device_token, payload):
        return self._device(device_code).kiosk_submit_punch(device_token, payload)

    @http.route(
        "/onehr/kiosk/api/timeoff",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def kiosk_timeoff(self, device_code, device_token, payload):
        return self._device(device_code).kiosk_submit_timeoff(device_token, payload)

    @http.route(
        "/onehr/kiosk/api/sync",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def kiosk_sync(self, device_code, device_token, events):
        return self._device(device_code).kiosk_sync_events(device_token, events)

    @http.route(
        "/onehr/kiosk/api/heartbeat",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def kiosk_heartbeat(self, device_code, device_token, payload=None):
        return self._device(device_code).kiosk_heartbeat(device_token, payload)

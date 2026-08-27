from odoo import _
from odoo.exceptions import AccessError


GROUP_KIOSK_OPERATOR = "onehr_mobile_kiosk.group_onehr_kiosk_operator"
GROUP_KIOSK_ADMIN = "onehr_mobile_kiosk.group_onehr_kiosk_admin"


def require_kiosk_operator(recordset):
    """Server-side authority check; UI visibility is never treated as security."""
    if not recordset.env.user.has_group(GROUP_KIOSK_OPERATOR):
        raise AccessError(_("OneHR Kiosk Operator permission is required."))
    return True


def require_kiosk_admin(recordset):
    """Configuration, token and dead-letter governance require Kiosk Admin."""
    if not recordset.env.user.has_group(GROUP_KIOSK_ADMIN):
        raise AccessError(_("OneHR Kiosk Administrator permission is required."))
    return True


from odoo import _
from odoo.exceptions import AccessError

GROUP_READER = "onehr_pnp.group_onehr_pnp_reader"
GROUP_OWNER = "onehr_pnp.group_onehr_pnp_owner"
GROUP_COMPLIANCE = "onehr_pnp.group_onehr_pnp_compliance"
GROUP_ADMIN = "onehr_pnp.group_onehr_pnp_admin"


def is_pnp_reader(env):
    return env.su or env.user.has_group(GROUP_READER)


def is_pnp_owner(env):
    return env.su or env.user.has_group(GROUP_OWNER)


def is_pnp_compliance(env):
    return env.su or env.user.has_group(GROUP_COMPLIANCE)


def is_pnp_admin(env):
    return env.su or env.user.has_group(GROUP_ADMIN)


def require_pnp_owner(recordset):
    if not is_pnp_owner(recordset.env):
        raise AccessError(_("This action requires PnP Policy Owner authority."))


def require_pnp_compliance(recordset):
    if not is_pnp_compliance(recordset.env):
        raise AccessError(_("This action requires PnP Compliance Officer authority."))


def require_pnp_admin(recordset):
    if not is_pnp_admin(recordset.env):
        raise AccessError(_("This action requires PnP Administrator authority."))


def display_notification(
    message,
    *,
    title="OneHR Policies & Procedures",
    notification_type="success",
):
    return {
        "type": "ir.actions.client",
        "tag": "display_notification",
        "params": {
            "title": title,
            "message": message,
            "type": notification_type,
            "sticky": False,
        },
    }


def open_record_action(*, name, res_model, res_id):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "res_id": res_id,
        "view_mode": "form",
        "target": "current",
    }


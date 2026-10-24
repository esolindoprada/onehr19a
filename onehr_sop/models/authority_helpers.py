
from odoo import _
from odoo.exceptions import AccessError

GROUP_READER = "onehr_sop.group_onehr_sop_reader"
GROUP_EDITOR = "onehr_sop.group_onehr_sop_editor"
GROUP_APPROVER = "onehr_sop.group_onehr_sop_approver"
GROUP_ADMIN = "onehr_sop.group_onehr_sop_admin"


def is_sop_reader(env):
    return env.is_superuser() or env.user.has_group(GROUP_READER)


def is_sop_editor(env):
    return env.is_superuser() or env.user.has_group(GROUP_EDITOR)


def is_sop_approver(env):
    return env.is_superuser() or env.user.has_group(GROUP_APPROVER)


def is_sop_admin(env):
    return env.is_superuser() or env.user.has_group(GROUP_ADMIN)


def require_sop_editor(recordset):
    if not is_sop_editor(recordset.env):
        raise AccessError(_("This action requires SOP Editor / QA authority."))


def require_sop_approver(recordset):
    if not is_sop_approver(recordset.env):
        raise AccessError(_("This action requires SOP Approver / Compliance authority."))


def require_sop_admin(recordset):
    if not is_sop_admin(recordset.env):
        raise AccessError(_("This action requires SOP Administrator authority."))


def notification(message, *, title="OneHR SOP", notification_type="success"):
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


def open_record(*, name, res_model, res_id):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "res_id": res_id,
        "view_mode": "form",
    }


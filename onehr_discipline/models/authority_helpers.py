
from odoo import _
from odoo.exceptions import AccessError

GROUP_INVESTIGATOR = "onehr_discipline.group_onehr_discipline_investigator"
GROUP_HRBP = "onehr_discipline.group_onehr_discipline_hrbp"
GROUP_MANAGER = "onehr_discipline.group_onehr_discipline_manager"
GROUP_LEGAL = "onehr_discipline.group_onehr_discipline_legal"


def is_investigator(env):
    return env.su or env.user.has_group(GROUP_INVESTIGATOR)


def is_hrbp(env):
    return env.su or env.user.has_group(GROUP_HRBP)


def is_manager(env):
    return env.su or env.user.has_group(GROUP_MANAGER)


def is_legal(env):
    return env.su or env.user.has_group(GROUP_LEGAL)


def require_investigator(recordset):
    if not is_investigator(recordset.env):
        raise AccessError(_("This action requires Discipline Investigator authority."))


def require_hrbp(recordset):
    if not is_hrbp(recordset.env):
        raise AccessError(_("This action requires Discipline HRBP authority."))


def require_manager(recordset):
    if not is_manager(recordset.env):
        raise AccessError(_("This action requires Discipline Manager authority."))


def require_legal(recordset):
    if not is_legal(recordset.env):
        raise AccessError(_("This action requires Discipline Legal / IR authority."))


def display_notification(
    message,
    *,
    title="OneHR Discipline",
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


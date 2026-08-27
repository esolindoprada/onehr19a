from odoo import _
from odoo.exceptions import AccessError

GROUP_PARTICIPANT = "onehr_appraisal.group_onehr_appraisal_participant"
GROUP_MANAGER = "onehr_appraisal.group_onehr_appraisal_manager"
GROUP_HR = "onehr_appraisal.group_onehr_appraisal_hr"
GROUP_ADMIN = "onehr_appraisal.group_onehr_appraisal_admin"

def is_appraisal_participant(env):
    return env.user.has_group(GROUP_PARTICIPANT)

def is_appraisal_manager(env):
    return env.user.has_group(GROUP_MANAGER)

def is_appraisal_hr(env):
    return env.user.has_group(GROUP_HR)

def is_appraisal_admin(env):
    return env.user.has_group(GROUP_ADMIN)

def require_appraisal_manager_or_hr(recordset):
    if not (is_appraisal_manager(recordset.env) or is_appraisal_hr(recordset.env)):
        raise AccessError(_("This action requires Appraisal Manager or Appraisal HR authority."))

def require_appraisal_hr(recordset):
    if not is_appraisal_hr(recordset.env):
        raise AccessError(_("This action requires Appraisal HR authority."))

def require_appraisal_admin(recordset):
    if not is_appraisal_admin(recordset.env):
        raise AccessError(_("This action requires Appraisal HR Manager authority."))

def display_notification(message, *, title="OneHR Appraisal", notification_type="success"):
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

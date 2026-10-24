
from odoo import _
from odoo.exceptions import AccessError

GROUP_READER = "onehr_job_description.group_onehr_jd_reader"
GROUP_EDITOR = "onehr_job_description.group_onehr_jd_editor"
GROUP_APPROVER = "onehr_job_description.group_onehr_jd_approver"
GROUP_ADMIN = "onehr_job_description.group_onehr_jd_admin"


def is_jd_reader(env):
    return env.user.has_group(GROUP_READER)


def is_jd_editor(env):
    return env.user.has_group(GROUP_EDITOR)


def is_jd_approver(env):
    return env.user.has_group(GROUP_APPROVER)


def is_jd_admin(env):
    return env.user.has_group(GROUP_ADMIN)


def require_jd_editor(recordset):
    if not is_jd_editor(recordset.env):
        raise AccessError(_("This action requires Job Description Editor authority."))


def require_jd_approver(recordset):
    if not is_jd_approver(recordset.env):
        raise AccessError(_("This action requires Job Description Approver authority."))


def require_jd_admin(recordset):
    if not is_jd_admin(recordset.env):
        raise AccessError(_("This action requires Job Description Administrator authority."))


def display_notification(
    message,
    *,
    title="OneHR Job Description",
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


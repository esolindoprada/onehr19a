from odoo import _
from odoo.exceptions import AccessError


GROUP_RECRUITER = "onehr_recruitment.group_onehr_recruiter"
GROUP_HIRING_MANAGER = "onehr_recruitment.group_onehr_hiring_manager"
GROUP_RECRUITMENT_MANAGER = "onehr_recruitment.group_onehr_recruitment_manager"


def require_group(recordset, group_xmlid, message=None):
    """Server-side authority gate; view visibility is never treated as security."""
    if not recordset.env.user.has_group(group_xmlid):
        raise AccessError(message or _("You do not have authority to perform this recruitment action."))


def require_recruiter(recordset):
    require_group(recordset, GROUP_RECRUITER, _("Recruiter authority is required."))


def require_hiring_manager(recordset):
    if not (
        recordset.env.user.has_group(GROUP_HIRING_MANAGER)
        or recordset.env.user.has_group(GROUP_RECRUITMENT_MANAGER)
    ):
        raise AccessError(_("Hiring Manager authority is required."))


def require_recruitment_manager(recordset):
    require_group(recordset, GROUP_RECRUITMENT_MANAGER, _("Recruitment Manager authority is required."))

from odoo import _
from odoo.exceptions import AccessError

GROUP_LINE_MANAGER = "onehr_employment_contract.group_onehr_contract_line_manager"
GROUP_OFFICER = "onehr_employment_contract.group_onehr_contract_officer"
GROUP_MANAGER = "onehr_employment_contract.group_onehr_contract_manager"


def require_group(recordset, group_xmlid, message):
    """Server-side business authority; UI visibility is never authorization."""
    if not recordset.env.user.has_group(group_xmlid):
        raise AccessError(message)


def require_contract_officer(recordset):
    require_group(recordset, GROUP_OFFICER, _("Contract Officer authority is required."))


def require_contract_manager(recordset):
    require_group(recordset, GROUP_MANAGER, _("Contract Manager authority is required."))

from odoo import _
from odoo.exceptions import AccessError


COREHR_OFFICER = "onehr_corehr.group_onehr_corehr_officer"
COREHR_MANAGER = "onehr_corehr.group_onehr_corehr_manager"
IDENTIFIER_STEWARD = "onehr_corehr.group_onehr_identifier_steward"
OH_OFFICER = "onehr_corehr.group_onehr_occupational_health_officer"


def open_records_action(*, name, res_model, domain=None, context=None):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": "list,form",
        "domain": domain or [],
        "context": context or {},
        "target": "current",
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


def require_any_group(env, *xmlids):
    if env.su or any(env.user.has_group(xmlid) for xmlid in xmlids):
        return
    raise AccessError(_("You are not authorized to perform this OneHR Core HR action."))


def require_corehr_officer(env):
    return require_any_group(env, COREHR_OFFICER, COREHR_MANAGER)


def require_corehr_manager(env):
    return require_any_group(env, COREHR_MANAGER)


def require_identifier_steward(env):
    return require_any_group(env, IDENTIFIER_STEWARD)


def require_occupational_health(env):
    return require_any_group(env, OH_OFFICER)

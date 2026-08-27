from odoo import _


def open_records_action(*, name, res_model, domain=None, context=None, view_mode="list,form", target="current"):
    """Build a conventional Odoo window action from readable business code."""
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": view_mode,
        "domain": domain or [],
        "context": context or {},
        "target": target,
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


def display_name_or_dash(record):
    return record.display_name if record else _("—")

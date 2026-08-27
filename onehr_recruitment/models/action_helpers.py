"""Small action helpers kept outside Odoo model inheritance.

Keeping UI-action dictionaries in ordinary functions makes business models
shorter and easier to audit or manually change without registry magic.
"""


def open_records_action(*, name, res_model, domain=None, context=None, view_mode="list,form"):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": view_mode,
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

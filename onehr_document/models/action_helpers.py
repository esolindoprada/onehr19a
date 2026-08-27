"""Small action and authorization helpers for OneHR Document.

Helpers are functions rather than plain-Python model base classes. Odoo 19 builds
registry classes dynamically; business model classes therefore use Odoo model
bases only.
"""

from odoo import _
from odoo.exceptions import AccessError, UserError


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


def open_wizard_action(*, name, res_model, context=None):
    return {
        "type": "ir.actions.act_window",
        "name": name,
        "res_model": res_model,
        "view_mode": "form",
        "target": "new",
        "context": context or {},
    }


def require_document_officer(env):
    if env.is_superuser():
        return
    if not env.user.has_group("onehr_document.group_onehr_document_officer"):
        raise AccessError(_("OneHR Document Officer access is required."))


def require_document_manager(env):
    if env.is_superuser():
        return
    if not env.user.has_group("onehr_document.group_onehr_document_manager"):
        raise AccessError(_("OneHR Document Manager access is required."))




def require_document_officer_or_compliance(env):
    if env.is_superuser():
        return
    if not (
        env.user.has_group("onehr_document.group_onehr_document_officer")
        or env.user.has_group("onehr_document.group_onehr_document_compliance")
    ):
        raise AccessError(_("OneHR Document Officer or Compliance access is required."))

def require_document_manager_or_compliance(env):
    if env.is_superuser():
        return
    if not (
        env.user.has_group("onehr_document.group_onehr_document_manager")
        or env.user.has_group("onehr_document.group_onehr_document_compliance")
    ):
        raise AccessError(_("OneHR Document Manager or Compliance access is required."))


def source_record_from_pair(env, source_model_id, source_res_id, *, require_read=True):
    """Resolve a controlled model/id pair without bypassing record security."""
    if not source_model_id and not source_res_id:
        return env["ir.model"]
    if not source_model_id or not source_res_id:
        raise UserError(_("Source Model and Source Record must either both be set or both be empty."))
    if source_res_id < 1:
        raise UserError(_("Source Record ID must be a positive integer."))

    model_name = source_model_id.model
    if not model_name:
        raise UserError(_("The selected source model is not available."))

    try:
        record = env[model_name].browse(source_res_id).exists()
    except KeyError as exc:
        raise UserError(_("The selected source model is not installed.")) from exc

    if not record:
        raise UserError(_("The selected source record does not exist."))

    if require_read:
        record.check_access("read")
    return record

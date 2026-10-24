
from markupsafe import Markup, escape
from werkzeug.exceptions import Forbidden, NotFound

from odoo import _, fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.fields import Command
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class OneHRPortalSelfService(CustomerPortal):
    _items_per_page = 20
    _max_attachments = 10
    _max_attachment_bytes = 10 * 1024 * 1024
    _max_total_attachment_bytes = 25 * 1024 * 1024

    def _portal_employee(self):
        return request.env.user.employee_id

    def _require_self_service_identity(self):
        employee = self._portal_employee()
        if not employee:
            raise Forbidden(_("Your user account is not linked to an employee record."))
        if not request.env.user.onehr_portal_self_service_enabled:
            raise Forbidden(_("OneHR self-service is disabled for this employee account."))
        return employee

    def _request_record(self, request_id):
        record = request.env["onehr.portal.request"].browse(request_id).exists()
        if not record:
            raise NotFound()
        try:
            record.check_access("read")
        except AccessError as exc:
            raise Forbidden() from exc
        return record

    def _render_new_request(self, *, selected_type=False, error=False, form_values=None):
        RequestType = request.env["onehr.portal.request.type"]
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "onehr_new_request",
                "request_types": RequestType.search([("active", "=", True), ("portal_enabled", "=", True)], order="sequence, name"),
                "selected_type": selected_type or RequestType,
                "error": error,
                "form_values": form_values or {},
            }
        )
        return request.render("onehr_portal_self_service.portal_request_new", values)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        can_self_service = (
            user.has_group("onehr_portal_self_service.group_onehr_portal_employee")
            or user.has_group("onehr_portal_self_service.group_onehr_portal_hr")
        )
        if "onehr_hr_request_count" in counters and can_self_service:
            values["onehr_hr_request_count"] = request.env["onehr.portal.request"].search_count(
                [("employee_user_id", "=", user.id)]
            )
        if "onehr_team_request_count" in counters and user.has_group(
            "onehr_portal_self_service.group_onehr_portal_manager"
        ):
            values["onehr_team_request_count"] = request.env["onehr.portal.request"].search_count(
                [("manager_user_id", "=", user.id), ("state", "=", "manager_review")]
            )
        return values

    @http.route(["/my/hr"], type="http", auth="user", website=True, methods=["GET"])
    def portal_my_hr(self, page=1, state="all", type_id=None, sortby="newest", **kw):
        self._require_self_service_identity()
        Request = request.env["onehr.portal.request"]
        domain = [("employee_user_id", "=", request.env.user.id)]

        if state and state != "all":
            domain.append(("state", "=", state))
        if type_id:
            try:
                domain.append(("type_id", "=", int(type_id)))
            except (TypeError, ValueError):
                pass

        sortings = {
            "newest": {"label": _("Newest"), "order": "create_date desc, id desc"},
            "oldest": {"label": _("Oldest"), "order": "create_date asc, id asc"},
            "deadline": {"label": _("SLA Deadline"), "order": "sla_deadline asc, id desc"},
            "priority": {"label": _("Priority"), "order": "priority desc, create_date desc"},
        }
        sortby = sortby if sortby in sortings else "newest"
        total = Request.search_count(domain)
        pager = portal_pager(
            url="/my/hr",
            total=total,
            page=int(page),
            step=self._items_per_page,
            url_args={"state": state, "type_id": type_id, "sortby": sortby},
        )
        records = Request.search(
            domain,
            order=sortings[sortby]["order"],
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        types = request.env["onehr.portal.request.type"].search([("active", "=", True), ("portal_enabled", "=", True)], order="sequence, name")
        dashboard = Request.onehr_my_hr_dashboard_payload()
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "onehr_my_hr",
                "requests": records,
                "request_types": types,
                "pager": pager,
                "selected_state": state,
                "selected_type_id": int(type_id) if str(type_id or "").isdigit() else False,
                "sortby": sortby,
                "searchbar_sortings": sortings,
                "dashboard": dashboard,
                "request_state_selection": Request._fields["state"].selection,
                "request_state_labels": dict(Request._fields["state"].selection),
            }
        )
        return request.render("onehr_portal_self_service.portal_my_hr", values)

    @http.route(["/my/hr/new"], type="http", auth="user", website=True, methods=["GET"])
    def portal_new_request(self, type_id=None, **kw):
        self._require_self_service_identity()
        types = request.env["onehr.portal.request.type"].search([("active", "=", True), ("portal_enabled", "=", True)], order="sequence, name")
        selected = request.env["onehr.portal.request.type"]
        if type_id and str(type_id).isdigit():
            selected = types.filtered(lambda item: item.id == int(type_id))[:1]
        return self._render_new_request(selected_type=selected)

    @http.route(["/my/hr/new"], type="http", auth="user", website=True, methods=["POST"])
    def portal_create_request(self, **post):
        employee = self._require_self_service_identity()
        RequestType = request.env["onehr.portal.request.type"]
        try:
            type_id = int(post.get("type_id") or 0)
        except (TypeError, ValueError):
            type_id = 0
        request_type = RequestType.browse(type_id).exists()
        if not request_type:
            raise Forbidden(_("Select a valid self-service Request Type."))
        request_type.check_access("read")
        if not request_type.active or not request_type.portal_enabled:
            raise Forbidden(_("The selected HR service is not currently available for self-service."))

        profile_change = {}
        if request_type.service_kind == "profile_change":
            for field_name in (
                "private_email",
                "private_phone",
                "private_street",
                "private_street2",
                "private_city",
                "private_zip",
            ):
                value = (post.get(field_name) or "").strip()
                if value:
                    profile_change[field_name] = value

        values = {
            "employee_id": employee.id,
            "type_id": request_type.id,
            "subject": (post.get("subject") or "").strip(),
            "description": (post.get("description") or "").strip(),
            "employee_note": (post.get("employee_note") or "").strip(),
            "priority": post.get("priority") or request_type.default_priority,
            "leave_type_code": (post.get("leave_type_code") or "").strip().upper(),
            "learning_session_reference": (post.get("learning_session_reference") or "").strip(),
            "document_category_code": (post.get("document_category_code") or "").strip().upper(),
            "document_title": (post.get("document_title") or "").strip(),
            "profile_change_json": profile_change,
        }
        try:
            if post.get("requested_date_from"):
                values["requested_date_from"] = fields.Date.to_date(post["requested_date_from"])
            if post.get("requested_date_to"):
                values["requested_date_to"] = fields.Date.to_date(post["requested_date_to"])
        except (TypeError, ValueError) as exc:
            return self._render_new_request(
                selected_type=request_type,
                error=_("Requested dates are not valid."),
                form_values=post,
            )

        if not values["subject"] or not values["description"]:
            return self._render_new_request(
                selected_type=request_type,
                error=_("Subject and Description are required."),
                form_values=post,
            )

        uploads = request.httprequest.files.getlist("attachments")
        if len(uploads) > self._max_attachments:
            return self._render_new_request(
                selected_type=request_type,
                error=_("A maximum of %s attachments is allowed per request.") % self._max_attachments,
                form_values=post,
            )

        try:
            # Read and validate uploads before creating the transaction. Attachments are
            # then created through mail.thread's standard message_post attachment path,
            # so portal code does not grant or bypass generic ir.attachment CRUD.
            attachment_payloads = []
            total_attachment_bytes = 0
            for upload in uploads:
                content = upload.read(self._max_attachment_bytes + 1)
                if not content:
                    continue
                if len(content) > self._max_attachment_bytes:
                    raise ValidationError(
                        _("Attachment '%s' exceeds the 10 MB self-service limit.")
                        % (upload.filename or _("Attachment"))
                    )
                total_attachment_bytes += len(content)
                if total_attachment_bytes > self._max_total_attachment_bytes:
                    raise ValidationError(
                        _("The combined attachment size exceeds the 25 MB self-service limit.")
                    )
                attachment_payloads.append((upload.filename or _("Attachment"), content))

            # The savepoint keeps browser validation human-friendly without leaving a
            # partial Draft behind when attachment or submission validation fails.
            with request.env.cr.savepoint():
                record = request.env["onehr.portal.request"].create(values)
                if attachment_payloads:
                    message = record.message_post(
                        body=_("Supporting attachment(s) uploaded through My HR."),
                        subtype_xmlid="mail.mt_comment",
                        attachments=attachment_payloads,
                    )
                    if message.attachment_ids:
                        record.write(
                            {
                                "attachment_ids": [
                                    Command.link(attachment.id)
                                    for attachment in message.attachment_ids
                                ]
                            }
                        )

                if post.get("submit_now") == "1":
                    record.action_submit()
        except (AccessError, UserError, ValidationError) as exc:
            return self._render_new_request(
                selected_type=request_type,
                error=str(exc),
                form_values=post,
            )
        return request.redirect(f"/my/hr/{record.id}")

    @http.route(["/my/hr/<int:request_id>"], type="http", auth="user", website=True, methods=["GET"])
    def portal_request_detail(self, request_id, **kw):
        record = self._request_record(request_id)
        values = self._prepare_portal_layout_values()
        portal_messages = record.message_ids.filtered(
            lambda message: (
                message.message_type == "comment"
                and (not message.subtype_id or not message.subtype_id.internal)
            )
        )[:20]
        values.update(
            {
                "page_name": "onehr_request_detail",
                "hr_request": record,
                "portal_messages": portal_messages,
                "is_owner": record.employee_user_id == request.env.user,
                "is_manager": record.manager_user_id == request.env.user and request.env.user.has_group(
                    "onehr_portal_self_service.group_onehr_portal_manager"
                ),
                "is_portal_hr": request.env.user.has_group(
                    "onehr_portal_self_service.group_onehr_portal_hr"
                ),
                "request_state_labels": dict(record._fields["state"].selection),
                "sla_status_labels": dict(record._fields["sla_status"].selection),
                "integration_status_labels": dict(record._fields["integration_status"].selection),
            }
        )
        return request.render("onehr_portal_self_service.portal_request_detail", values)

    @http.route(["/my/hr/<int:request_id>/submit"], type="http", auth="user", website=True, methods=["POST"])
    def portal_submit_request(self, request_id, **post):
        record = self._request_record(request_id)
        record.action_submit()
        return request.redirect(f"/my/hr/{record.id}")

    @http.route(["/my/hr/<int:request_id>/cancel"], type="http", auth="user", website=True, methods=["POST"])
    def portal_cancel_request(self, request_id, **post):
        record = self._request_record(request_id)
        record.action_cancel()
        return request.redirect(f"/my/hr/{record.id}")

    @http.route(["/my/hr/<int:request_id>/comment"], type="http", auth="user", website=True, methods=["POST"])
    def portal_request_comment(self, request_id, **post):
        record = self._request_record(request_id)
        comment = (post.get("comment") or "").strip()
        if comment:
            record.message_post(
                body=Markup("<p>{}</p>").format(escape(comment)),
                subtype_xmlid="mail.mt_comment",
            )
        return request.redirect(f"/my/hr/{record.id}")

    @http.route(["/my/team"], type="http", auth="user", website=True, methods=["GET"])
    def portal_my_team(self, page=1, **kw):
        if not request.env.user.has_group("onehr_portal_self_service.group_onehr_portal_manager"):
            raise Forbidden()
        Request = request.env["onehr.portal.request"]
        domain = [("manager_user_id", "=", request.env.user.id), ("state", "=", "manager_review")]
        total = Request.search_count(domain)
        pager = portal_pager(url="/my/team", total=total, page=int(page), step=self._items_per_page)
        records = Request.search(
            domain,
            order="priority desc, sla_deadline asc, submitted_at asc, id asc",
            limit=self._items_per_page,
            offset=pager["offset"],
        )
        values = self._prepare_portal_layout_values()
        values.update(
            {
                "page_name": "onehr_my_team",
                "team_requests": records,
                "pager": pager,
            }
        )
        return request.render("onehr_portal_self_service.portal_my_team", values)

    @http.route(["/my/team/<int:request_id>/approve"], type="http", auth="user", website=True, methods=["POST"])
    def portal_manager_approve(self, request_id, **post):
        record = self._request_record(request_id)
        record.action_manager_approve((post.get("note") or "").strip())
        return request.redirect("/my/team")

    @http.route(["/my/team/<int:request_id>/reject"], type="http", auth="user", website=True, methods=["POST"])
    def portal_manager_reject(self, request_id, **post):
        record = self._request_record(request_id)
        record.action_manager_reject((post.get("note") or "").strip())
        return request.redirect("/my/team")


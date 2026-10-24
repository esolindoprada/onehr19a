
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRPortalCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create(
            {"name": f"OneHR Portal Other Company {cls.__name__}"}
        )

        cls.group_employee = cls.env.ref(
            "onehr_portal_self_service.group_onehr_portal_employee"
        )
        cls.group_manager = cls.env.ref(
            "onehr_portal_self_service.group_onehr_portal_manager"
        )
        cls.group_hr = cls.env.ref(
            "onehr_portal_self_service.group_onehr_portal_hr"
        )
        cls.group_admin = cls.env.ref(
            "onehr_portal_self_service.group_onehr_portal_admin"
        )
        cls.group_internal = cls.env.ref("base.group_user")

        suffix = cls.__name__.lower()

        def make_user(name, login, group, company):
            return cls.env["res.users"].with_context(no_reset_password=True).create(
                {
                    "name": name,
                    "login": login,
                    "company_id": company.id,
                    "company_ids": [Command.set([company.id])],
                    "group_ids": [Command.set(group.ids)],
                }
            )

        cls.employee_user = make_user(
            "Portal Employee", f"portal_employee_{suffix}", cls.group_employee, cls.company
        )
        cls.manager_user = make_user(
            "Portal Manager", f"portal_manager_{suffix}", cls.group_manager, cls.company
        )
        cls.other_manager_user = make_user(
            "Other Portal Manager", f"portal_other_manager_{suffix}", cls.group_manager, cls.company
        )
        cls.hr_user = make_user(
            "Portal HR", f"portal_hr_{suffix}", cls.group_hr, cls.company
        )
        cls.admin_user = make_user(
            "Portal Admin", f"portal_admin_{suffix}", cls.group_admin, cls.company
        )
        cls.plain_user = make_user(
            "Plain Internal User", f"portal_plain_{suffix}", cls.group_internal, cls.company
        )

        cls.manager_employee = cls.env["hr.employee"].create(
            {
                "name": "Portal Direct Manager",
                "company_id": cls.company.id,
                "user_id": cls.manager_user.id,
            }
        )
        cls.other_manager_employee = cls.env["hr.employee"].create(
            {
                "name": "Other Portal Manager",
                "company_id": cls.company.id,
                "user_id": cls.other_manager_user.id,
            }
        )
        cls.employee = cls.env["hr.employee"].create(
            {
                "name": "Portal Employee",
                "company_id": cls.company.id,
                "user_id": cls.employee_user.id,
                "parent_id": cls.manager_employee.id,
                "onehr_portal_self_service_enabled": True,
            }
        )

    def make_type(self, **extra):
        values = {
            "name": "General HR Service Test",
            "code": f"GEN_{self._testMethodName}",
            "company_id": self.company.id,
            "service_kind": "generic",
            "manager_approval_required": True,
            "hr_approval_required": True,
            "sla_hours": 48,
            "reminder_hours_before": 12,
        }
        values.update(extra)
        return self.env["onehr.portal.request.type"].with_user(self.hr_user).create(values)

    def make_request(self, request_type=None, **extra):
        request_type = request_type or self.make_type()
        values = {
            "type_id": request_type.id,
            "subject": "Employment letter assistance",
            "description": "Please assist with this HR service request.",
        }
        values.update(extra)
        return self.env["onehr.portal.request"].with_user(self.employee_user).create(values)

    def submit_request(self, request_type=None, **extra):
        record = self.make_request(request_type=request_type, **extra)
        record.with_user(self.employee_user).action_submit()
        return record


from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRKioskCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR Kiosk Other Company"})

        cls.group_operator = cls.env.ref("onehr_mobile_kiosk.group_onehr_kiosk_operator")
        cls.group_admin = cls.env.ref("onehr_mobile_kiosk.group_onehr_kiosk_admin")

        def make_user(name, login, group, company=None, companies=None):
            company = company or cls.company
            companies = companies or [company]
            return cls.env["res.users"].with_context(no_reset_password=True).create({
                "name": name,
                "login": login,
                "company_id": company.id,
                "company_ids": [Command.set([item.id for item in companies])],
                "group_ids": [Command.set(group.ids)],
            })

        cls.operator = make_user("Kiosk Service A", "onehr_kiosk_operator_test", cls.group_operator)
        cls.other_operator = make_user(
            "Kiosk Service Other",
            "onehr_kiosk_other_operator_test",
            cls.group_operator,
            company=cls.other_company,
            companies=[cls.other_company],
        )
        cls.admin = make_user(
            "Kiosk Administrator",
            "onehr_kiosk_admin_test",
            cls.group_admin,
            companies=[cls.company, cls.other_company],
        )

        cls.location = cls.env["hr.work.location"].create({
            "name": "Kiosk HQ",
            "company_id": cls.company.id,
            "onehr_site_code": "KIOSK-HQ",
            "onehr_latitude": -8.6500,
            "onehr_longitude": 115.2167,
        })
        cls.other_location = cls.env["hr.work.location"].create({
            "name": "Kiosk Other HQ",
            "company_id": cls.other_company.id,
            "onehr_site_code": "KIOSK-OTHER",
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Kiosk Employee",
            "company_id": cls.company.id,
            "barcode": "KIOSK-EMP-QR",
            "onehr_employee_number": "KSK-EMP-001",
            "work_location_id": cls.location.id,
        })
        cls.other_employee = cls.env["hr.employee"].create({
            "name": "Other Kiosk Employee",
            "company_id": cls.other_company.id,
            "barcode": "OTHER-KIOSK-QR",
            "onehr_employee_number": "KSK-EMP-OTHER",
            "work_location_id": cls.other_location.id,
        })

        cls.device = cls.env["onehr.kiosk.device"].with_user(cls.admin).create({
            "name": "Kiosk Gate A",
            "company_id": cls.company.id,
            "service_user_id": cls.operator.id,
            "work_location_id": cls.location.id,
            "device_kind": "shared_kiosk",
            "platform": "web",
        })
        cls.token = cls.device.with_user(cls.admin)._issue_token()
        cls.device.with_user(cls.admin).action_activate()

        cls.other_device = cls.env["onehr.kiosk.device"].with_user(cls.admin).create({
            "name": "Other Company Kiosk",
            "company_id": cls.other_company.id,
            "service_user_id": cls.other_operator.id,
            "work_location_id": cls.other_location.id,
        })
        cls.other_token = cls.other_device.with_user(cls.admin)._issue_token()
        cls.other_device.with_user(cls.admin).action_activate()

    def punch_payload(self, event_id, mode="auto", event_at=None, **extra):
        values = {
            "identity": self.employee.barcode,
            "credential_type": "qr",
            "client_event_id": event_id,
            "event_at": fields.Datetime.to_string(event_at or fields.Datetime.now()),
            "punch_mode": mode,
        }
        values.update(extra)
        return values

    def submit(self, payload):
        return self.device.with_user(self.operator).kiosk_submit_punch(self.token, payload)

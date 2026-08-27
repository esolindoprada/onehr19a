import base64
from datetime import timedelta

from odoo import fields
from odoo.fields import Command
from odoo.tests.common import TransactionCase


class OneHRAttendanceCommon(TransactionCase):
    """Shared enterprise test fixture using normal OneHR Attendance authorities."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.other_company = cls.env["res.company"].create({"name": "OneHR Attendance Other Company"})

        cls.group_officer = cls.env.ref("onehr_attendance.group_onehr_attendance_officer")
        cls.group_manager = cls.env.ref("onehr_attendance.group_onehr_attendance_manager")

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

        cls.officer = make_user("Attendance Officer Test", "onehr_attendance_officer_test", cls.group_officer)
        cls.manager = make_user(
            "Attendance Manager Test",
            "onehr_attendance_manager_test",
            cls.group_manager,
            companies=[cls.company, cls.other_company],
        )
        cls.other_officer = make_user(
            "Other Attendance Officer Test",
            "onehr_attendance_other_officer_test",
            cls.group_officer,
            company=cls.other_company,
            companies=[cls.other_company],
        )

        cls.department = cls.env["hr.department"].create({
            "name": "Attendance Operations",
            "company_id": cls.company.id,
            "onehr_code": "ATT-OPS",
        })
        cls.job = cls.env["hr.job"].create({
            "name": "Attendance Operator",
            "company_id": cls.company.id,
            "onehr_code": "ATT-JOB",
        })
        cls.work_address = cls.env["res.partner"].create({"name": "Attendance HQ Address"})
        cls.location = cls.env["hr.work.location"].create({
            "name": "Attendance HQ",
            "company_id": cls.company.id,
            "address_id": cls.work_address.id,
            "onehr_site_code": "ATT-HQ",
            "onehr_latitude": -6.200000,
            "onehr_longitude": 106.816666,
        })
        cls.grade = cls.env["onehr.grade"].create({
            "code": "ATT-G1", "name": "Attendance Grade", "company_id": cls.company.id,
        })
        cls.position = cls.env["onehr.position"].create({
            "code": "ATT-POS-1",
            "name": "Attendance Operator Seat",
            "company_id": cls.company.id,
            "department_id": cls.department.id,
            "job_id": cls.job.id,
            "work_location_id": cls.location.id,
            "grade_id": cls.grade.id,
            "authorized_headcount": 5,
            "authorized_fte": 5.0,
            "status": "open",
        })

        cls.manager_employee = cls.env["hr.employee"].create({
            "name": "Attendance Reporting Manager",
            "company_id": cls.company.id,
            "user_id": cls.manager.id,
            "work_location_id": cls.location.id,
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Attendance Employee",
            "company_id": cls.company.id,
            "parent_id": cls.manager_employee.id,
            "work_location_id": cls.location.id,
            "onehr_employee_number": "ATT-0001",
            "barcode": "ATTBADGE0001",
            "work_email": "attendance.employee@example.test",
        })
        cls.employee_2 = cls.env["hr.employee"].create({
            "name": "Attendance Employee Two",
            "company_id": cls.company.id,
            "parent_id": cls.manager_employee.id,
            "work_location_id": cls.location.id,
            "onehr_employee_number": "ATT-0002",
            "barcode": "ATTBADGE0002",
            "work_email": "attendance.employee2@example.test",
        })
        cls.other_employee = cls.env["hr.employee"].create({
            "name": "Other Attendance Employee",
            "company_id": cls.other_company.id,
        })

        cls.today = fields.Date.today()

    def make_shift(self, code="DAY", **overrides):
        values = {
            "name": f"Shift {code}",
            "code": code,
            "company_id": self.company.id,
            "resource_calendar_id": self.company.resource_calendar_id.id,
            "timezone": "UTC",
            "start_hour": 8.0,
            "end_hour": 17.0,
            "valid_from": self.today - timedelta(days=30),
            "monday": True,
            "tuesday": True,
            "wednesday": True,
            "thursday": True,
            "friday": True,
            "saturday": True,
            "sunday": True,
        }
        values.update(overrides)
        return self.env["onehr.shift"].with_user(self.manager).create(values)

    def activate_shift(self, shift):
        shift.with_user(self.manager).action_activate()
        return shift

    def make_pattern(self, shifts, code="PAT", **overrides):
        values = {
            "name": f"Pattern {code}",
            "code": code,
            "company_id": self.company.id,
            "version": 1,
            "anchor_date": self.today,
            "valid_from": self.today - timedelta(days=30),
            "shift_ids": [Command.set(shifts.ids)],
            "cycle_codes": ",".join([shift.code for shift in shifts]) if shifts else "OFF",
        }
        values.update(overrides)
        return self.env["onehr.shift.pattern"].with_user(self.manager).create(values)

    def make_schedule(self, employee=None, shift=None, pattern=None, **overrides):
        employee = employee or self.employee
        values = {
            "company_id": employee.company_id.id,
            "employee_id": employee.id,
            "valid_from": self.today - timedelta(days=10),
            "valid_to": self.today + timedelta(days=60),
        }
        if shift:
            values["shift_id"] = shift.id
        if pattern:
            values["pattern_id"] = pattern.id
        values.update(overrides)
        return self.env["onehr.shift.assignment"].with_user(self.manager).create(values)

    def activate_schedule(self, schedule):
        schedule.with_user(self.manager).action_activate()
        return schedule

    def make_attendance_for_shift(self, shift, day=None, employee=None, start_delta=0, end_delta=0, **overrides):
        day = day or self.today
        employee = employee or self.employee
        planned_start, planned_end = shift._planned_interval_utc(day)
        values = {
            "employee_id": employee.id,
            "check_in": planned_start + timedelta(minutes=start_delta),
            "check_out": planned_end + timedelta(minutes=end_delta),
            "onehr_source_channel": "manual",
        }
        values.update(overrides)
        return self.env["hr.attendance"].with_user(self.officer).create(values)

    def approve_native_overtime_if_needed(self, attendance):
        pending = attendance.linked_overtime_ids.filtered(lambda line: line.status == "to_approve")
        if pending:
            pending.with_user(self.manager).action_approve()
        return attendance

    def make_import_batch(self, csv_text, key="BATCH-001", **overrides):
        values = {
            "company_id": self.company.id,
            "source_system": "FINGERPRINT",
            "idempotency_key": key,
            "filename": f"{key}.csv",
            "upload_file": base64.b64encode(csv_text.encode("utf-8")),
            "identifier_type": "employee_number",
            "timezone": "UTC",
        }
        values.update(overrides)
        return self.env["onehr.attendance.import.batch"].with_user(self.officer).create(values)

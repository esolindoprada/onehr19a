
from odoo import fields
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from .common import OneHRCoreHRCommon


@tagged("post_install", "-at_install", "onehr_corehr")
class TestOccupationalHealth(OneHRCoreHRCommon):
    def test_14_work_incident_controlled_workflow_and_immutability(self):
        incident = self.env["onehr.work.incident"].with_user(self.oh_officer).create(
            {
                "employee_id": self.employee.id,
                "incident_type": "near_miss",
                "severity": "moderate",
                "description": "Near miss in controlled test.",
                "closure_summary": "Root cause reviewed; preventive action recorded.",
            }
        )
        incident.with_user(self.oh_officer).action_report()
        incident.with_user(self.oh_officer).action_start_review()
        incident.with_user(self.oh_officer).action_close()
        self.assertEqual(incident.state, "closed")

        with self.assertRaises(AccessError):
            incident.with_user(self.oh_officer).write({"description": "rewrite closed evidence"})

        with self.assertRaises(AccessError):
            incident.with_user(self.oh_officer).unlink()

    def test_15_medical_finalization_requires_superseding_correction(self):
        assessment = self.env["onehr.medical.assessment"].with_user(self.oh_officer).create(
            {
                "employee_id": self.employee.id,
                "assessment_type": "fitness",
                "fitness_classification": "fit_with_restrictions",
                "restrictions_summary": "Temporary lifting limit.",
            }
        )
        assessment.with_user(self.oh_officer).action_finalize()
        self.assertEqual(assessment.state, "finalized")

        with self.assertRaises(AccessError):
            assessment.with_user(self.oh_officer).write(
                {"restrictions_summary": "rewrite finalized evidence"}
            )

        action = assessment.with_user(self.oh_officer).action_create_correction()
        correction = self.env["onehr.medical.assessment"].browse(action["res_id"])
        assessment.invalidate_recordset(["state"])
        self.assertEqual(assessment.state, "superseded")
        self.assertEqual(correction.state, "draft")
        self.assertEqual(correction.supersedes_id, assessment)

    def test_16_accommodation_record_exposes_only_derived_employee_need(self):
        record = self.env["onehr.disability.record"].with_user(self.oh_officer).create(
            {
                "employee_id": self.employee.id,
                "category": "other",
                "accommodation_required": True,
                "accommodation_summary": "Ergonomic workstation required.",
            }
        )
        record.with_user(self.oh_officer).action_activate()
        self.employee.invalidate_recordset(["onehr_accommodation_required"])
        self.assertTrue(self.employee.onehr_accommodation_required)

        record.with_user(self.oh_officer).action_close()
        self.employee.invalidate_recordset(["onehr_accommodation_required"])
        self.assertFalse(self.employee.onehr_accommodation_required)

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRRecruitmentCommon


@tagged("post_install", "-at_install", "onehr_recruitment")
class TestRecruitmentRequisition(OneHRRecruitmentCommon):
    def test_01_sequence_and_native_applicant_link(self):
        self.assertNotEqual(self.requisition.name, "New")
        self.assertEqual(self.applicant.onehr_requisition_id, self.requisition)
        self.assertEqual(self.requisition.applicant_count, 1)

    def test_02_headcount_and_company_constraints(self):
        with self.assertRaises(ValidationError):
            self.env["onehr.recruitment.requisition"].with_user(self.manager).create({
                "title": "Invalid",
                "company_id": self.company.id,
                "job_id": self.job.id,
                "requested_headcount": 0,
                "reason": "Invalid headcount",
            })
        with self.assertRaises(ValidationError):
            self.env["onehr.recruitment.requisition"].with_user(self.manager).create({
                "title": "Wrong Company",
                "company_id": self.company.id,
                "job_id": self.other_job.id,
                "requested_headcount": 1,
                "reason": "Invalid company scope",
            })

    def test_03_approval_callback_preserves_source_ownership(self):
        self.requisition.with_user(self.manager).write({"state": "pending_approval", "submitted_at": fields.Datetime.now()})
        self.requisition.with_user(self.manager)._on_approval_finalized("approve", self.env["onehr.approval.request"])
        self.assertEqual(self.requisition.state, "approved")
        self.assertEqual(self.requisition.approved_headcount, self.requisition.requested_headcount)

    def test_04_submitted_requisition_demand_is_immutable(self):
        self.requisition.with_user(self.manager).write({"state": "approved", "approved_headcount": 1})
        with self.assertRaises(AccessError):
            self.requisition.with_user(self.manager).write({"requested_headcount": 2})

    def test_05_recruiting_and_fill_gate(self):
        self.requisition.with_user(self.manager).write({"state": "approved", "approved_headcount": 1})
        self.requisition.with_user(self.manager).action_start_recruiting()
        self.assertEqual(self.requisition.state, "recruiting")
        with self.assertRaises(UserError):
            self.requisition.with_user(self.manager).action_mark_filled()

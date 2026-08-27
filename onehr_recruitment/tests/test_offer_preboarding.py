from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from .common import OneHRRecruitmentCommon


@tagged("post_install", "-at_install", "onehr_recruitment")
class TestOfferPreboarding(OneHRRecruitmentCommon):
    def test_11_offer_total_and_date_validation(self):
        offer = self.make_offer()
        self.assertEqual(offer.total_cash_compensation, 11500000)
        with self.assertRaises(ValidationError):
            self.make_offer(expiry_date=fields.Date.today() - timedelta(days=1))

    def test_12_offer_approval_callback_and_term_freeze(self):
        offer = self.make_offer()
        offer.with_user(self.manager).write({"state": "pending_approval"})
        offer.with_user(self.manager)._on_approval_finalized("approve", self.env["onehr.approval.request"])
        self.assertEqual(offer.state, "approved")
        with self.assertRaises(AccessError):
            offer.with_user(self.manager).write({"base_salary": 20000000})

    def test_13_offer_acceptance_requires_sent_state(self):
        offer = self.make_offer()
        with self.assertRaises(UserError):
            offer.with_user(self.manager).action_accept()
        offer.with_user(self.manager).write({"state": "approved"})
        offer.with_user(self.manager).action_mark_sent()
        offer.with_user(self.manager).action_accept()
        self.assertEqual(offer.state, "accepted")

    def test_14_preboarding_requires_accepted_offer_to_ready(self):
        offer = self.make_offer()
        preboarding = self.env["onehr.preboarding"].with_user(self.manager).create({
            "applicant_id": self.applicant.id,
            "requisition_id": self.requisition.id,
            "offer_id": offer.id,
            "planned_start_date": fields.Date.today() + timedelta(days=30),
        })
        with self.assertRaises(UserError):
            preboarding.with_user(self.manager).action_ready()

    def test_15_only_one_active_preboarding_per_applicant(self):
        offer = self.make_offer()
        offer.with_user(self.manager).write({"state": "accepted"})
        self.env["onehr.preboarding"].with_user(self.manager).create({
            "applicant_id": self.applicant.id,
            "offer_id": offer.id,
            "planned_start_date": offer.proposed_start_date,
        })
        with self.assertRaises(ValidationError):
            self.env["onehr.preboarding"].with_user(self.manager).create({
                "applicant_id": self.applicant.id,
                "offer_id": offer.id,
                "planned_start_date": offer.proposed_start_date,
            })

"""Unattended runs: find, write, send, spaced out, only inside the window."""
import os
import random
import unittest
from datetime import datetime

from reachdesk import autopilot, channels, service
from tests.test_flow import Base, FakeSMTP

MONDAY_10 = datetime(2026, 11, 9, 10, 0)
SUNDAY_10 = datetime(2026, 11, 8, 10, 0)
MONDAY_22 = datetime(2026, 11, 9, 22, 0)


class Autopilot(Base):
    def setUp(self):
        super().setUp()
        os.environ["REACHDESK_SMTP_PASSWORD"] = "test-only"
        for key, value in (("smtp_host", "smtp.example.test"), ("smtp_user", "me@example.test"), ("smtp_from", "me@example.test")):
            service.set_setting(self.conn, key, value)
        service.update_campaign(self.conn, self.cid, {"auto_email": 1})
        self.pauses = []

    def run_at(self, moment, smtp=None):
        smtp = smtp or FakeSMTP()
        report = autopilot.run_once(self.conn, lambda config: smtp, sleep=self.pauses.append, clock=lambda: moment,
                                    rng=random.Random(1), fetch=False)
        return report, smtp

    def test_sends_without_anyone_and_spaces_the_emails(self):
        for n in (1, 2, 3):
            self.person(n, email=f"p{n}@maple.example", consent_basis="published_business_contact")
        report, smtp = self.run_at(MONDAY_10)
        self.assertEqual(len(smtp.sent), 3)
        self.assertEqual(report["campaigns"]["ca-consultants"]["email"]["sent"], 3)
        self.assertEqual(len(self.pauses), 2)  # a pause between sends, none before the first
        self.assertTrue(all(45 <= p <= 150 for p in self.pauses))

    def test_queues_but_does_not_send_outside_the_window(self):
        self.person(email="sara@maple.example", consent_basis="published_business_contact")
        for moment in (SUNDAY_10, MONDAY_22):
            report, smtp = self.run_at(moment)
            self.assertEqual(smtp.sent, [])
            self.assertFalse(report["in_window"])
        self.assertEqual(len(service.list_queue(self.conn, self.cid)), 1)
        _, smtp = self.run_at(MONDAY_10)
        self.assertEqual(len(smtp.sent), 1)

    def test_campaigns_without_auto_email_are_left_alone(self):
        report, _ = self.run_at(MONDAY_10)
        self.assertNotIn("parsa-career", report["campaigns"])

    def test_safety_rules_still_apply(self):
        self.person(1, email="noconsent@maple.example")
        opted_out = self.person(2, email="ok@maple.example", consent_basis="published_business_contact")
        service.suppress(self.conn, opted_out["contact_key"], "opt_out")
        _, smtp = self.run_at(MONDAY_10)
        self.assertEqual(smtp.sent, [])

    def test_job_ad_asking_for_cvs_by_email_is_answered(self):
        cid = self.career["id"]
        service.update_campaign(self.conn, cid, {"auto_email": 1})
        service.add_item(self.conn, cid, {
            "kind": "job", "title": "Computer Vision Engineer", "company": "acme", "url": "https://jobs.example/cv-1",
            "body": "Computer vision, deep learning, PyTorch. Send your CV to jobs@acme.example",
        })
        _, smtp = self.run_at(MONDAY_10)
        self.assertEqual([m["To"] for m in smtp.sent], ["jobs@acme.example"])
        self.assertIn("Computer Vision Engineer", smtp.sent[0].get_content())

    def test_job_ad_without_an_invitation_is_not_emailed(self):
        cid = self.career["id"]
        service.update_campaign(self.conn, cid, {"auto_email": 1})
        service.add_item(self.conn, cid, {
            "kind": "job", "title": "Computer Vision Engineer", "url": "https://jobs.example/cv-2",
            "body": "Computer vision, deep learning. Questions? privacy@acme.example",
        })
        _, smtp = self.run_at(MONDAY_10)
        self.assertEqual(smtp.sent, [])

    def test_bad_settings_fall_back_to_defaults(self):
        service.set_setting(self.conn, "autopilot_hours", "nonsense")
        service.set_setting(self.conn, "autopilot_gap_max", "1")
        cfg = autopilot.config(self.conn)
        self.assertEqual((cfg["start"], cfg["end"]), (9, 17))
        self.assertGreaterEqual(cfg["gap_max"], cfg["gap_min"])

    def test_dispatch_without_pause_is_unchanged(self):
        self.person(email="sara@maple.example", consent_basis="published_business_contact")
        service.build_queue(self.conn, self.cid)
        smtp = FakeSMTP()
        self.assertEqual(channels.dispatch_email(self.conn, self.cid, lambda c: smtp)["sent"], 1)

    def test_job_boards_are_fetched_at_most_every_six_hours(self):
        from unittest import mock

        cid = self.career["id"]
        service.update_campaign(self.conn, cid, {"auto_email": 1})
        with mock.patch.object(service, "fetch_sources", return_value={"created": 0}) as fetch:
            for _ in range(3):
                autopilot.run_once(self.conn, lambda c: FakeSMTP(), sleep=self.pauses.append, clock=lambda: MONDAY_10)
        self.assertEqual(fetch.call_count, 1)

    def test_schedule_commands(self):
        cmds = autopilot.schedule_commands("python", "run.py", "w.db")
        self.assertIn("schtasks", cmds["windows"])
        self.assertIn("autopilot", cmds["linux_mac_cron"])


if __name__ == "__main__":
    unittest.main()

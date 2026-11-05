"""The end-to-end rules: connect first, consent, opt-out, caps, automatic email."""
import random
import smtplib
import unittest

from reachdesk import channels, db, importers, messages, plans, seed, service

SECRET = bytes(range(32))
PUBLIC = plans.public_key(SECRET).hex()


def owner(conn):
    import os

    os.environ["REACHDESK_LICENSE_PUBKEY"] = PUBLIC
    service.set_setting(conn, "license", plans.issue_license(SECRET, "owner", "test"))


class Base(unittest.TestCase):
    def setUp(self):
        self.conn = db.connect(":memory:")
        seed.seed(self.conn)
        owner(self.conn)
        self.consult = service.get_campaign(self.conn, slug="ca-consultants")
        self.career = service.get_campaign(self.conn, slug="parsa-career")
        self.cid = self.consult["id"]
        self.consult = service.update_campaign(self.conn, self.cid, {"website": "https://client.example.com", "sender_name": "Sam", "sender_contact": "sam@client.example.com"})

    def person(self, n=1, **extra):
        data = {
            "kind": "person", "full_name": f"Sara Ahmadi{chr(64 + n)}", "title": "Immigration Consultant, RCIC",
            "location": "Toronto, Canada", "url": f"https://www.linkedin.com/in/sara-ahmadi-{chr(96 + n)}", **extra,
        }
        return service.add_item(self.conn, extra.pop("campaign", self.cid), data)[0]


class ConnectFirst(Base):
    def test_stranger_gets_a_short_note_without_a_link(self):
        self.person()
        self.assertEqual(service.build_queue(self.conn, self.cid)["created"], 1)
        draft = service.list_queue(self.conn, self.cid)[0]
        self.assertEqual(draft["step"], "connect")
        self.assertLessEqual(len(draft["body"]), 200)
        self.assertNotIn("http", draft["body"])
        self.assertTrue(draft["body"].startswith("Hi Sara,"))

    def test_acceptance_unlocks_the_real_message_automatically(self):
        item = self.person()
        service.build_queue(self.conn, self.cid)
        note = service.list_queue(self.conn, self.cid)[0]
        service.mark_sent(self.conn, note["id"])
        self.assertEqual(service.get_item(self.conn, item["id"])["connection_state"], "pending")

        report = service.build_queue(self.conn, self.cid)
        self.assertEqual(report["created"], 0)

        service.mark_accepted(self.conn, item["id"])
        ready = service.list_queue(self.conn, self.cid)
        self.assertEqual([d["step"] for d in ready], ["message"])
        self.assertIn("https://client.example.com", ready[0]["body"])
        self.assertIn('Reply "stop"', ready[0]["body"])

    def test_importing_connections_csv_detects_acceptance(self):
        item = self.person()
        service.build_queue(self.conn, self.cid)
        service.mark_sent(self.conn, service.list_queue(self.conn, self.cid)[0]["id"])
        csv_text = (
            "Notes:\n\"Some people may not show.\"\n\n"
            "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
            f"Sara,AhmadiA,{item['url']},,Maple,Consultant,01 Nov 2026\n"
        )
        result = service.import_csv(self.conn, self.cid, csv_text)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(service.get_item(self.conn, item["id"])["connection_state"], "connected")
        self.assertEqual(service.list_queue(self.conn, self.cid)[0]["step"], "message")

    def test_existing_connection_goes_straight_to_a_message(self):
        self.person(connection_state="connected", consent_basis="existing_connection")
        service.build_queue(self.conn, self.cid)
        self.assertEqual(service.list_queue(self.conn, self.cid)[0]["step"], "message")


class Safety(Base):
    def test_opt_out_stops_everything_across_campaigns(self):
        item = self.person(connection_state="connected", consent_basis="existing_connection")
        service.build_queue(self.conn, self.cid)
        draft = service.list_queue(self.conn, self.cid)[0]
        service.mark_sent(self.conn, draft["id"])
        service.record_reply(self.conn, draft["id"], opt_out=True)

        other, _ = service.add_item(self.conn, self.career["id"], {"kind": "person", "title": "Recruiter", "url": item["url"], "connection_state": "connected"})
        report = service.build_queue(self.conn, self.career["id"])
        self.assertEqual(report["created"], 0)
        self.assertEqual(report["skipped"].get("suppressed"), 1)

    def test_commercial_message_blocked_without_consent_basis(self):
        self.person(connection_state="connected", consent_basis="none")
        report = service.build_queue(self.conn, self.cid)
        self.assertEqual(report["created"], 0)
        self.assertEqual(report["skipped"].get("no_consent_basis"), 1)

    def test_post_saying_no_contact_is_respected(self):
        service.add_item(self.conn, self.career["id"], {"kind": "post", "title": "CTO", "body": "We are hiring a computer vision engineer. DM me. No recruiters please.", "url": "https://www.linkedin.com/feed/update/1"})
        report = service.build_queue(self.conn, self.career["id"])
        self.assertEqual(report["created"], 0)
        self.assertEqual(report["skipped"].get("asked_not_to_be_contacted"), 1)

    def test_comment_post_is_kept_for_the_user_not_messaged(self):
        item, _ = service.add_item(self.conn, self.career["id"], {"kind": "post", "body": "We're hiring a deep learning engineer! Comment below if interested.", "url": "https://www.linkedin.com/feed/update/2"})
        self.assertEqual(item["status"], "saved")
        self.assertEqual(service.build_queue(self.conn, self.career["id"])["created"], 0)
        self.assertEqual(service.get_item(self.conn, item["id"])["status"], "saved")

    def test_daily_cap_and_no_duplicates(self):
        service.update_campaign(self.conn, self.cid, {"daily_cap": 3})
        for n in range(1, 8):
            self.person(n)
        self.assertEqual(service.build_queue(self.conn, self.cid)["created"], 3)
        self.assertEqual(service.build_queue(self.conn, self.cid)["created"], 0)
        keys = [d["contact_key"] for d in service.list_queue(self.conn, self.cid)]
        self.assertEqual(len(keys), len(set(keys)))

    def test_same_person_is_not_contacted_from_two_campaigns(self):
        item = self.person()
        service.build_queue(self.conn, self.cid)
        service.add_item(self.conn, self.career["id"], {"kind": "person", "title": "Recruiter", "url": item["url"]})
        report = service.build_queue(self.conn, self.career["id"])
        self.assertEqual(report["skipped"].get("recently_contacted"), 1)

    def test_missing_website_blocks_the_template_not_silently_sends(self):
        service.update_campaign(self.conn, self.cid, {"website": ""})
        self.person(connection_state="connected", consent_basis="existing_connection")
        report = service.build_queue(self.conn, self.cid)
        self.assertEqual(report["created"], 0)
        self.assertEqual(report["skipped"].get("no_valid_template"), 1)
        self.assertTrue(any("website" in p for p in report["template_problems"]))

    def test_erase_removes_data_and_blocks_recontact(self):
        item = self.person()
        service.forget_item(self.conn, item["id"])
        self.assertIsNone(service.get_item(self.conn, item["id"]))
        again = self.person()
        self.assertEqual(service.build_queue(self.conn, self.cid)["skipped"].get("suppressed"), 1)
        self.assertEqual(again["full_name"], "Sara AhmadiA")

    def test_reimport_preserves_rating(self):
        item = self.person()
        service.rate_item(self.conn, item["id"], 5, "great_role")
        again = self.person()
        self.assertEqual(again["id"], item["id"])
        self.assertEqual(again["stars"], 5)


class Templates(Base):
    def test_low_confidence_name_uses_neutral_greeting(self):
        ctx = messages.context({"first_name": "Jane", "name_confidence": 0.3}, {})
        self.assertEqual(ctx["greeting"], "Hello,")

    def test_no_broken_output_when_fields_are_missing(self):
        text = messages.render("{greeting} I saw your work{at_company}. {role_hook}Thanks.", messages.context({}, {}))
        self.assertEqual(text, "Hello, I saw your work. Thanks.")

    def test_commercial_lint(self):
        problems = messages.lint("Buy now {website}", self.consult, "message")
        self.assertTrue(any("opt_out" in p for p in problems))
        self.assertTrue(any("sender_name" in p for p in problems))

    def test_connect_note_lint(self):
        self.assertTrue(messages.lint("Hi {website}", self.consult, "connect"))
        self.assertTrue(messages.lint("x" * 300, self.consult, "connect"))
        self.assertTrue(messages.lint("{nonsense}", self.consult, "connect"))

    def test_all_seed_templates_are_valid(self):
        for campaign in (self.consult, self.career):
            for variant in service.list_variants(self.conn, campaign["id"]):
                with self.subTest(variant=variant["name"]):
                    self.assertEqual(variant["problems"], [])

    def test_career_intro_is_personal_and_includes_site(self):
        item, _ = service.add_item(self.conn, self.career["id"], {"kind": "person", "full_name": "Sarah Chen", "title": "Recruiter", "url": "https://www.linkedin.com/in/sarah-chen", "connection_state": "connected"})
        service.build_queue(self.conn, self.career["id"], random.Random(0))
        body = service.list_queue(self.conn, self.career["id"])[0]["body"]
        self.assertTrue(body.startswith("Hi Sarah,"))
        self.assertIn("https://parsavictor.github.io/", body)
        self.assertNotIn("{", body)

    def test_bandit_prefers_what_earns_replies(self):
        variants = [{"id": 1}, {"id": 2}]
        stats = {1: {"sent": 100, "replies": 2}, 2: {"sent": 100, "replies": 30}}
        rng = random.Random(5)
        wins = sum(messages.pick_variant(variants, stats, rng)["id"] == 2 for _ in range(200))
        self.assertGreater(wins, 190)


class FakeSMTP:
    def __init__(self, fail_for=()):
        self.sent, self.fail_for, self.closed = [], set(fail_for), False

    def send_message(self, message):
        if message["To"] in self.fail_for:
            raise smtplib.SMTPRecipientsRefused({message["To"]: (550, b"no")})
        self.sent.append(message)

    def quit(self):
        self.closed = True


class AutoEmail(Base):
    def setUp(self):
        super().setUp()
        import os

        os.environ["REACHDESK_SMTP_PASSWORD"] = "test-only"
        for key, value in (("smtp_host", "smtp.example.test"), ("smtp_user", "me@example.test"), ("smtp_from", "me@example.test")):
            service.set_setting(self.conn, key, value)
        service.update_campaign(self.conn, self.cid, {"auto_email": 1})

    def run_dispatch(self, smtp=None):
        smtp = smtp or FakeSMTP()
        service.build_queue(self.conn, self.cid)
        return channels.dispatch_email(self.conn, self.cid, lambda config: smtp), smtp

    def test_permitted_contact_is_emailed_without_any_click(self):
        self.person(email="sara@maple.example", consent_basis="published_business_contact")
        report, smtp = self.run_dispatch()
        self.assertEqual(report["sent"], 1)
        message = smtp.sent[0]
        self.assertEqual(message["To"], "sara@maple.example")
        body = message.get_content()
        self.assertIn("Hi Sara,", body)
        self.assertIn("https://client.example.com", body)
        self.assertIn('Reply "stop"', body)
        self.assertIn("sam@client.example.com", body)
        self.assertTrue(smtp.closed)

    def test_no_consent_basis_means_no_email(self):
        self.person(email="sara@maple.example", consent_basis="none")
        report, smtp = self.run_dispatch()
        self.assertEqual(smtp.sent, [])
        self.assertEqual(report["sent"], 0)

    def test_opt_out_after_queueing_is_blocked_at_send_time(self):
        item = self.person(email="sara@maple.example", consent_basis="published_business_contact")
        service.build_queue(self.conn, self.cid)
        self.conn.execute("INSERT INTO suppressions (contact_key, reason, created_at) VALUES (?,?,?)", (item["contact_key"], "late", db.now()))
        smtp = FakeSMTP()
        report = channels.dispatch_email(self.conn, self.cid, lambda config: smtp)
        self.assertEqual(report["blocked"], 1)
        self.assertEqual(smtp.sent, [])

    def test_daily_cap_applies_to_email(self):
        service.update_campaign(self.conn, self.cid, {"daily_cap": 2})
        for n in range(1, 6):
            self.person(n, email=f"p{n}@maple.example", consent_basis="published_business_contact")
        report, smtp = self.run_dispatch()
        self.assertEqual(report["sent"], 2)
        report2, smtp2 = self.run_dispatch()
        self.assertEqual(report2["sent"], 0)

    def test_failed_recipient_does_not_stop_the_rest(self):
        self.person(1, email="bad@maple.example", consent_basis="published_business_contact")
        self.person(2, email="good@maple.example", consent_basis="published_business_contact")
        report, smtp = self.run_dispatch(FakeSMTP(fail_for=["bad@maple.example"]))
        self.assertEqual((report["sent"], report["failed"]), (1, 1))

    def test_invited_cv_post_is_emailed_for_the_career_campaign(self):
        cid = self.career["id"]
        service.update_campaign(self.conn, cid, {"auto_email": 1})
        service.add_item(self.conn, cid, {"kind": "post", "body": "We're hiring a Computer Vision Engineer. Send your resume to talent@acme.example", "url": "https://www.linkedin.com/feed/update/9"})
        service.build_queue(self.conn, cid)
        smtp = FakeSMTP()
        report = channels.dispatch_email(self.conn, cid, lambda config: smtp)
        self.assertEqual(report["sent"], 1)
        self.assertIn("Computer Vision Engineer", smtp.sent[0].get_content())

    def test_free_plan_cannot_auto_send(self):
        self.person(email="sara@maple.example", consent_basis="published_business_contact")
        service.set_setting(self.conn, "license", "")
        report, smtp = self.run_dispatch()
        self.assertEqual(smtp.sent, [])
        self.assertIn("Pro", report["reason"])


class Csv(unittest.TestCase):
    def test_linkedin_connections_format(self):
        text = "﻿Notes:\n\"When exporting...\"\n\nFirst Name,Last Name,URL,Email Address,Company,Position,Connected On\nAli,Rezaei,https://www.linkedin.com/in/ali-r,,Maple,RCIC,01 Jan 2026\n"
        records = importers.parse_csv(text)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["full_name"], "Ali Rezaei")
        self.assertEqual(records[0]["connection_state"], "connected")
        self.assertEqual(records[0]["consent_basis"], "existing_connection")

    def test_generic_format_and_blank_rows(self):
        records = importers.parse_csv("Name,Job Title,Company,City\nAli R,Advisor,Maple,Ottawa\n,,,\n")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["location"], "Ottawa")
        self.assertNotIn("connection_state", records[0])

    def test_export_neutralises_formula_injection(self):
        text = importers.export_csv([{"full_name": "=HYPERLINK(1)", "title": "@cmd"}], ["full_name", "title"])
        self.assertIn("'=HYPERLINK", text)
        self.assertIn("'@cmd", text)

    def test_javascript_url_never_gets_stored(self):
        conn = db.connect(":memory:")
        seed.seed(conn)
        cid = service.get_campaign(conn, slug="parsa-career")["id"]
        item, _ = service.add_item(conn, cid, {"kind": "person", "full_name": "A B", "url": "javascript:alert(1)"}, enforce=False)
        self.assertEqual(item["url"], "")


class PlanLimits(unittest.TestCase):
    def test_free_plan_limits(self):
        conn = db.connect(":memory:")
        seed.seed(conn)
        with self.assertRaises(service.LimitError):
            service.create_campaign(conn, "third", "Third")
        cid = service.get_campaign(conn, slug="parsa-career")["id"]
        with self.assertRaises(service.LimitError):
            service.fetch_sources(conn, cid)
        with self.assertRaises(service.LimitError):
            service.export_items(conn, cid)
        with self.assertRaises(service.LimitError):
            service.update_campaign(conn, cid, {"auto_email": 1})
        self.assertEqual(service.update_campaign(conn, cid, {"daily_cap": 999})["daily_cap"], 10)


class Licenses(unittest.TestCase):
    def test_rfc8032_vector(self):
        secret = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
        public = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        signature = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        self.assertEqual(plans.public_key(secret), public)
        self.assertEqual(plans.sign(secret, b""), signature)
        self.assertTrue(plans.verify(public, b"", signature))
        self.assertFalse(plans.verify(public, b"x", signature))

    def test_tampered_and_expired_keys_fail(self):
        token = plans.issue_license(SECRET, "pro", "Acme")
        self.assertEqual(plans.read_license(token, PUBLIC)["plan"], "pro")
        tag, body, sig = token.split(".")
        forged = plans._b64(b'{"customer":"Acme","expires":"","plan":"owner"}')
        self.assertIsNone(plans.read_license(f"{tag}.{forged}.{sig}", PUBLIC))
        self.assertIsNone(plans.read_license(plans.issue_license(SECRET, "pro", "A", "2020-01-01"), PUBLIC))
        other = plans.issue_license(bytes(32), "owner", "Thief")
        self.assertIsNone(plans.read_license(other, PUBLIC))
        self.assertIsNone(plans.read_license("garbage", PUBLIC))


if __name__ == "__main__":
    unittest.main()

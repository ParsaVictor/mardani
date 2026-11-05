import unittest

from reachdesk import textparse as tp


class Names(unittest.TestCase):
    def test_real_names(self):
        cases = {
            "Sarah Chen": "Sarah",
            "Dr. Sara Ahmadi, RCIC": "Sara",
            "JOHN SMITH": "John",
            "Marie-Claire Dubois MBA": "Marie-Claire",
            "🚀 Ali Rezaei 🇨🇦": "Ali",
            "Ali Rezaei | Immigration Advisor": "Ali",
            "محمد پارسا کرکوتی": "محمد",
        }
        for raw, first in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(tp.parse_name(raw)["first_name"], first)

    def test_never_guesses_when_unsure(self):
        for raw in ("Maple Immigration Inc.", "Northern Consulting Group", "J. Smith", "", "LinkedIn Member", "12345", "HR Team"):
            with self.subTest(raw=raw):
                self.assertEqual(tp.parse_name(raw)["first_name"], "")

    def test_name_from_profile_url(self):
        result = tp.name_from_profile_url("https://ca.linkedin.com/in/jane-doe-12a3b4/?trk=x")
        self.assertEqual(result["first_name"], "Jane")
        self.assertLessEqual(result["confidence"], 0.6)
        self.assertEqual(tp.name_from_profile_url("https://www.linkedin.com/in/x8392")["first_name"], "")


class Urls(unittest.TestCase):
    def test_dangerous_schemes_are_rejected(self):
        for url in ("javascript:alert(1)", "data:text/html,x", "file:///c:/x", "", "http://"):
            self.assertEqual(tp.safe_url(url), "")

    def test_canonical_linkedin_identity(self):
        a = tp.contact_key("https://ca.linkedin.com/in/Jane-Doe/?utm=1")
        b = tp.contact_key("https://www.linkedin.com/in/jane-doe")
        self.assertEqual(a, b)
        self.assertEqual(tp.contact_key(email="A@B.com"), "em:a@b.com")


class Intent(unittest.TestCase):
    def check(self, text, intents=(), flags=()):
        result = tp.analyze_post(text)
        for intent in intents:
            self.assertIn(intent, result["intents"], text)
        for flag in flags:
            self.assertIn(flag, result["flags"], text)
        return result

    def test_calls_to_action(self):
        self.check("We're hiring! Comment below if you are interested.", ["hiring", "cta_comment"])
        self.check("Looking for a CV engineer, DM me your portfolio", ["cta_dm"])
        self.check("Send your resume to jobs@acme.com", ["cta_cv"])
        self.check("Nous recrutons! Envoyez votre CV", ["hiring", "cta_cv"])
        self.check("برای استخدام رزومه خود را بفرستید و دایرکت بدهید", ["hiring", "cta_cv", "cta_dm"])

    def test_hiring_at_the_start_of_a_line(self):
        self.check("Hiring a full stack developer! Comment below.", ["hiring"])
        self.assertNotIn("hiring", tp.analyze_post("The cost of hiring a developer keeps rising.")["intents"])

    def test_plain_word_comment_is_not_a_call_to_action(self):
        self.assertNotIn("cta_comment", tp.analyze_post("Thanks for your comment yesterday, no comment on the news.")["intents"])

    def test_no_contact_is_detected(self):
        self.check("We are hiring. No recruiters please.", flags=["no_contact"])
        self.check("Please don't DM me about this.", flags=["no_contact"])

    def test_job_seeker_is_not_hiring(self):
        result = self.check("I am looking for a new job. #OpenToWork", flags=["seeker"])
        self.assertNotIn("hiring", result["intents"])

    def test_engagement_bait(self):
        self.check('Comment "GUIDE" and I will send the free PDF', flags=["engagement_bait"])

    def test_extracts_email_and_role(self):
        result = tp.analyze_post("We're hiring a Senior Computer Vision Engineer. CVs to talent@acme.io")
        self.assertEqual(result["email"], "talent@acme.io")
        self.assertIn("Computer Vision Engineer", result["role_hint"])


class Paste(unittest.TestCase):
    def test_linkedin_post_copy(self):
        text = """Feed post
Sarah Chen
Sarah Chen
• 2nd
Talent Acquisition Lead at Acme AI
3h •
We're hiring a Deep Learning Engineer in Toronto.
Send your resume to sarah@acme.ai
Like
Comment
Repost
Send"""
        result = tp.parse_paste(text, "https://www.linkedin.com/feed/update/urn:li:activity:1/")
        self.assertEqual(result["kind"], "post")
        self.assertEqual(result["first_name"], "Sarah")
        self.assertEqual(result["company"], "Acme AI")
        self.assertEqual(result["email"], "sarah@acme.ai")
        self.assertIn("cta_cv", result["intents"])
        self.assertNotIn("Repost", result["body"])

    def test_profile_copy(self):
        result = tp.parse_paste("Ali Rezaei\nRCIC at Maple Immigration", "https://www.linkedin.com/in/ali-rezaei/")
        self.assertEqual(result["kind"], "person")
        self.assertEqual(result["first_name"], "Ali")
        self.assertEqual(result["company"], "Maple Immigration")

    def test_sentence_is_not_a_name(self):
        result = tp.parse_paste("We are hiring engineers.\nJoin our team in Vancouver.")
        self.assertEqual(result["first_name"], "")


class SourceFiles(unittest.TestCase):
    def test_python_sources_are_clean_utf8_without_bom(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        files = list((root / "src").rglob("*.py")) + list((root / "src").rglob("*.js"))
        self.assertTrue(files)
        for path in files:
            data = path.read_bytes()
            self.assertFalse(data.startswith(b"\xef\xbb\xbf"), path)
            text = data.decode("utf-8")
            self.assertNotIn("Ø", text, f"mojibake in {path}")

    def test_seed_keeps_the_persian_keyword(self):
        from reachdesk import seed

        self.assertIn("مشاور", seed.CONSULTANTS["keywords"]["core"])


if __name__ == "__main__":
    unittest.main()

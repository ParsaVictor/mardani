"""The send desk: one card per person with the profile link and the exact text."""
import json
import tempfile
import unittest
from pathlib import Path

from reachdesk import cli, db, desk, service
from tests.test_flow import Base
from tests import test_server_sources


class Desk(Base):
    def test_cards_have_profile_link_and_personal_text(self):
        self.person(1)
        self.person(2, connection_state="connected", consent_basis="existing_connection")
        data = desk.entries(self.conn, self.cid)
        self.assertEqual(len(data["cards"]), 2)
        steps = {c["step"]: c for c in data["cards"]}
        connect, message = steps["connect"], steps["message"]
        self.assertTrue(connect["url"].startswith("https://www.linkedin.com/in/sara-ahmadi-"))
        self.assertTrue(connect["text"].startswith("Hi Sara,"))
        self.assertLessEqual(len(connect["text"]), data["campaign"]["note_limit"])
        self.assertIn("https://client.example.com", message["text"])
        self.assertTrue(connect["why"])

    def test_email_is_left_to_the_autopilot(self):
        service.update_campaign(self.conn, self.cid, {"auto_email": 1})
        self.person(email="sara@maple.example", consent_basis="published_business_contact")
        self.assertEqual(desk.entries(self.conn, self.cid)["cards"], [])

    def test_standalone_file_is_self_contained_and_safe(self):
        self.person(1, title="Consultant </script><script>alert(1)</script>")
        page = desk.standalone_html(desk.entries(self.conn, self.cid))
        self.assertIn("window.DESK_DATA", page)
        self.assertNotIn('src="/desk.js"', page)
        self.assertNotIn("</script><script>alert(1)", page)
        self.assertIn("linkedin.com/in/sara-ahmadi-a", page)

    def test_cli_writes_the_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "w.db"
            conn = db.connect(str(path))
            from reachdesk import seed

            seed.seed(conn)
            conn.close()
            out = Path(tmp) / "desk.html"
            self.assertEqual(cli.main(["--db", str(path), "desk", "ca-consultants", "--out", str(out)]), 0)
            self.assertIn("window.DESK_DATA", out.read_text(encoding="utf-8"))


class DeskServer(unittest.TestCase):
    # Reuse the running-server fixture without running Server's own tests again.
    setUpClass = test_server_sources.Server.__dict__["setUpClass"]
    tearDownClass = test_server_sources.Server.__dict__["tearDownClass"]
    call = test_server_sources.Server.call

    def test_desk_page_and_api(self):
        status, body, headers = self.call("GET", "/desk")
        self.assertEqual(status, 200)
        self.assertIn(b"/desk.js", body)
        status, body, _ = self.call("GET", "/api/desk?campaign=parsa-career")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertEqual(data["campaign"]["slug"], "parsa-career")
        self.assertIn("cards", data)
        self.assertEqual(self.call("GET", "/api/desk?campaign=nope")[0], 404)

if __name__ == "__main__":
    unittest.main()

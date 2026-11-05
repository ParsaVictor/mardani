import http.client
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path

from reachdesk import db, seed, server, sources


class Parsers(unittest.TestCase):
    def test_greenhouse(self):
        jobs = sources.parse_greenhouse({"jobs": [{"title": "CV Eng", "absolute_url": "https://x/1", "location": {"name": "Toronto"}, "content": "&lt;p&gt;Hello &amp;amp; welcome&lt;/p&gt;"}]}, "acme")
        self.assertEqual(jobs[0]["location"], "Toronto")
        self.assertEqual(jobs[0]["body"], "Hello & welcome")

    def test_lever(self):
        jobs = sources.parse_lever([{"text": "ML", "hostedUrl": "https://x/2", "categories": {"location": "Remote"}, "descriptionPlain": "Body"}], "acme")
        self.assertEqual((jobs[0]["title"], jobs[0]["location"]), ("ML", "Remote"))

    def test_ashby_hides_unlisted(self):
        jobs = sources.parse_ashby({"jobs": [{"title": "A", "isListed": True}, {"title": "B", "isListed": False}]}, "acme")
        self.assertEqual([j["title"] for j in jobs], ["A"])

    def test_remotive_and_arbeitnow(self):
        self.assertEqual(sources.parse_remotive({"jobs": [{"title": "R", "candidate_required_location": "Canada", "description": "<b>x</b>"}]})[0]["body"], "x")
        self.assertIn("remote", sources.parse_arbeitnow({"data": [{"title": "A", "location": "Berlin", "remote": True}]})[0]["location"])

    def test_slug_cannot_redirect_the_request(self):
        for slug in ("../../etc", "a/b", "x?y=1", "", "http://evil.test"):
            with self.subTest(slug=slug), self.assertRaises(ValueError):
                sources.fetch({"type": "greenhouse", "slug": slug})
        with self.assertRaises(ValueError):
            sources.fetch({"type": "linkedin"})


class Server(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        cls.path = str(Path(cls.tmp.name) / "w.db")
        conn = db.connect(cls.path)
        seed.seed(conn)
        cls.cid = conn.execute("SELECT id FROM campaigns WHERE slug='parsa-career'").fetchone()["id"]
        conn.close()
        cls.server = server.make_server(cls.path, 0)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.tmp.cleanup()

    def call(self, method, path, body=None, headers=None):
        client = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        all_headers = {"X-ReachDesk": "1", "Content-Type": "application/json", **(headers or {})}
        client.request(method, path, json.dumps(body) if body is not None else None, all_headers)
        response = client.getresponse()
        raw = response.read()
        result = response.status, raw, dict(response.getheaders())
        client.close()
        return result

    def test_static_pages_have_security_headers(self):
        for path in ("/", "/app.js", "/style.css"):
            status, _, headers = self.call("GET", path)
            self.assertEqual(status, 200)
            self.assertIn("default-src 'self'", headers["Content-Security-Policy"])

    def test_only_loopback_binding(self):
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_dns_rebinding_host_is_refused(self):
        self.assertEqual(self.call("GET", "/api/bootstrap", headers={"Host": "evil.example"})[0], 403)

    def test_cross_site_write_is_refused(self):
        path = f"/api/campaigns/{self.cid}/paste"
        self.assertEqual(self.call("POST", path, {"text": "x"}, {"Origin": "https://evil.example"})[0], 403)
        client = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        client.request("POST", path, "{}", {"Content-Type": "text/plain"})
        self.assertEqual(client.getresponse().status, 403)
        client.close()

    def test_refused_write_reply_survives_a_slow_body(self):
        """The server must read a refused body, or closing can reset the reply away (Windows CI)."""
        body = b"x" * 70000
        client = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        client.putrequest("POST", f"/api/campaigns/{self.cid}/paste")
        client.putheader("Origin", "https://evil.example")
        client.putheader("Content-Length", str(len(body)))
        client.endheaders()
        time.sleep(0.2)  # the reply is ready before the body arrives
        client.send(body)
        self.assertEqual(client.getresponse().status, 403)
        client.close()

    def test_full_api_round_trip(self):
        status, raw, _ = self.call("POST", f"/api/campaigns/{self.cid}/paste", {"text": "Sarah Chen\nRecruiter at Acme\nWe're hiring a Deep Learning Engineer. Comment below!", "url": "https://www.linkedin.com/feed/update/55"})
        self.assertEqual(status, 200)
        item = json.loads(raw)["item"]
        self.assertEqual(item["first_name"], "Sarah")
        self.assertEqual(item["status"], "saved")
        status, raw, _ = self.call("POST", f"/api/items/{item['id']}/rate", {"stars": 4, "reason": "great_role"})
        self.assertEqual(json.loads(raw)["stars"], 4)
        status, raw, _ = self.call("GET", f"/api/items?campaign={self.cid}&kind=post&status=saved")
        self.assertTrue(any(i["id"] == item["id"] for i in json.loads(raw)))
        self.assertEqual(self.call("GET", f"/api/insights?campaign={self.cid}")[0], 200)
        self.assertEqual(self.call("GET", f"/api/searches?campaign={self.cid}")[0], 200)
        self.assertEqual(self.call("POST", f"/api/campaigns/{self.cid}/queue", {})[0], 200)

    def test_ratings_retrain_in_the_background(self):
        ids = []
        for n in range(8):
            _, raw, _ = self.call("POST", f"/api/campaigns/{self.cid}/paste", {"text": f"Person Number\nRecruiter at Co\nBackground test post {n} about robots.", "url": f"https://www.linkedin.com/feed/update/bg{n}"})
            ids.append(json.loads(raw)["item"]["id"])
        for n, item_id in enumerate(ids):
            status, raw, _ = self.call("POST", f"/api/items/{item_id}/rate", {"stars": 5 if n % 2 else 1})
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(raw)["stars"], 5 if n % 2 else 1)
        deadline = time.monotonic() + 60
        trained = False
        while time.monotonic() < deadline and not trained:
            conn = db.connect(self.path)
            found = conn.execute("SELECT n FROM models WHERE campaign_id=?", (self.cid,)).fetchone()
            conn.close()
            trained = bool(found) and found["n"] >= 8
            time.sleep(0.2)
        self.assertTrue(trained, "the model was not retrained after the ratings")

    def test_errors_are_clean(self):
        self.assertEqual(self.call("GET", "/api/nope")[0], 404)
        self.assertEqual(self.call("POST", "/api/items/999999/rate", {"stars": 3})[0], 404)
        self.assertEqual(self.call("POST", "/api/items/1/rate", {"stars": 9})[0], 400)
        self.assertEqual(self.call("POST", f"/api/campaigns/{self.cid}/fetch", {})[0], 402)
        self.assertEqual(self.call("POST", "/api/license", {"token": "forged"})[0], 400)

    def test_path_traversal_serves_nothing(self):
        self.assertEqual(self.call("GET", "/../../pyproject.toml")[0], 404)
        self.assertEqual(self.call("GET", "/static/../db.py")[0], 404)


if __name__ == "__main__":
    unittest.main()

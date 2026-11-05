"""Does the ranking actually learn? Measured on a held-out synthetic set, not asserted by hand."""
import random
import unittest

from reachdesk import db, scoring, seed, service

# Both groups look identical to the keyword rules. Only the user's hidden taste,
# expressed through ratings, separates them, so any gain here is real learning.
WANTED = ["Machine Learning Engineer, Medical Imaging", "Machine Learning Engineer, Robotics", "Machine Learning Engineer, Satellites"]
UNWANTED = ["Machine Learning Engineer, Ads", "Machine Learning Engineer, Fraud", "Machine Learning Engineer, Crypto"]
WANTED_TEXT = "radiology scans surgical robots drones aerial hospital sensors"
UNWANTED_TEXT = "advertising auctions clicks revenue funnels trading tokens"


def make(rng, good):
    title = rng.choice(WANTED if good else UNWANTED)
    extra = " ".join(rng.sample((WANTED_TEXT if good else UNWANTED_TEXT).split(), 3))
    return {"kind": "job", "title": title, "company": f"Co{rng.randint(1, 9999)}", "body": f"We build AI. {extra} python", "url": f"https://jobs.example.com/{rng.random()}", "location": "Remote"}


def precision_at(items, k=10):
    ranked = sorted(items, key=lambda i: i["score"], reverse=True)[:k]
    return sum(i["_good"] for i in ranked) / k


class LearningImprovesRanking(unittest.TestCase):
    def test_precision_rises_with_ratings(self):
        rng = random.Random(42)
        conn = db.connect(":memory:")
        seed.seed(conn)
        cid = service.get_campaign(conn, slug="parsa-career")["id"]

        holdout = []
        for i in range(60):
            good = i % 2 == 0
            item, _ = service.add_item(conn, cid, make(rng, good), enforce=False)
            holdout.append((item["id"], good))

        def measure():
            items = [{**service.get_item(conn, iid), "_good": good} for iid, good in holdout]
            return precision_at(items)

        before = measure()
        curve = {}
        for i in range(40):
            good = i % 2 == 0
            item, _ = service.add_item(conn, cid, make(rng, good), enforce=False)
            liked = good if rng.random() > 0.1 else not good  # 10% of ratings are mistakes
            service.rate_item(conn, item["id"], 5 if liked else 1, "great_role" if liked else "wrong_role")
            if i + 1 in (5, 10, 20, 40):
                curve[i + 1] = measure()

        print(f"\n  held-out precision@10: before={before:.2f} after ratings={curve}")
        self.assertLessEqual(before, 0.6)
        self.assertEqual(curve[5], before)  # no model yet, by design
        self.assertGreaterEqual(curve[20], 0.8)
        self.assertGreaterEqual(curve[40], 0.9)

    def test_insights_show_the_improvement(self):
        rng = random.Random(1)
        conn = db.connect(":memory:")
        seed.seed(conn)
        cid = service.get_campaign(conn, slug="parsa-career")["id"]
        for i in range(40):
            good = i % 2 == 0
            item, _ = service.add_item(conn, cid, make(rng, good), enforce=False)
            service.rate_item(conn, item["id"], 5 if good else 1, "great_role" if good else "wrong_role")
        learning = service.insights(conn, cid)["learning"]
        self.assertEqual(learning["ratings"], 40)
        self.assertGreater(learning["alpha"], 0)
        self.assertGreaterEqual(learning["recent_accuracy"], learning["early_accuracy"])
        self.assertTrue(learning["likes"])
        self.assertTrue(learning["dislikes"])


class BlameAssignment(unittest.TestCase):
    def test_wrong_location_does_not_punish_skills(self):
        base = {"kind": "job", "title": "Computer Vision Engineer", "company": "Acme", "body": "opencv"}
        rated = []
        for i in range(8):
            rated.append({**base, "location": "Berlin", "stars": 1, "reason": "wrong_location"})
            rated.append({**base, "location": "Toronto", "stars": 5, "reason": "great_location"})
        weights = scoring.train(rated)
        self.assertLess(weights.get("l:berlin", 0), -0.1)
        self.assertGreater(weights.get("l:toronto", 0), 0.1)
        self.assertLess(abs(weights.get("t:computer", 0)), abs(weights["l:berlin"]))

    def test_fast_path_matches_the_full_calculation(self):
        rng = random.Random(9)
        data = [{**make(rng, i % 2 == 0), "stars": 5 if i % 2 == 0 else 1} for i in range(20)]
        weights = scoring.train(data)
        item = make(rng, True)
        score, learned = scoring.predict_explain(weights, item)
        self.assertAlmostEqual(score, scoring.predict(weights, item), places=9)
        self.assertEqual(sorted(learned), sorted(scoring.explain_model(weights, item)))

    def test_no_model_until_both_likes_and_dislikes(self):
        self.assertEqual(scoring.blend_weight(50, False), 0.0)
        self.assertEqual(scoring.blend_weight(3, True), 0.0)
        self.assertGreater(scoring.blend_weight(10, True), 0.0)

    def test_training_is_deterministic(self):
        rng = random.Random(3)
        data = [{**make(rng, i % 2 == 0), "stars": 5 if i % 2 == 0 else 1} for i in range(20)]
        self.assertEqual(scoring.train(data), scoring.train(data))


class Rules(unittest.TestCase):
    def setUp(self):
        self.keywords = seed.CONSULTANTS["keywords"]

    def score(self, **item):
        return scoring.rule_score(item, self.keywords)[0]

    def test_canadian_consultant_ranks_high(self):
        self.assertGreaterEqual(self.score(title="Immigration Consultant, RCIC", location="Toronto, Ontario, Canada"), 0.6)

    def test_outside_canada_is_capped(self):
        self.assertLessEqual(self.score(title="Immigration Consultant", location="London, UK"), 0.2)
        self.assertLessEqual(self.score(title="Consultant", location="Vancouver, Washington, USA"), 0.2)

    def test_short_province_codes_do_not_match_prose(self):
        score, why = scoring.rule_score({"title": "Painter", "body": "I work on walls", "location": ""}, self.keywords)
        self.assertNotIn("location mentioned in text", why)
        self.assertEqual(score, 0.0)

    def test_term_needs_a_word_boundary(self):
        self.assertEqual(self.score(title="Consultantship Manager", location=""), 0.0)


if __name__ == "__main__":
    unittest.main()

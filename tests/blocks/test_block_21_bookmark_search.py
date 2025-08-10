import unittest
import importlib.util
from pathlib import Path

# Load the root-level app.py explicitly (avoids the app/ package shadowing)
ROOT = Path(__file__).resolve().parents[2]
APP_FILE = ROOT / "app.py"
spec = importlib.util.spec_from_file_location("flask_app_module", APP_FILE)
flask_app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flask_app_module)
flask_app = flask_app_module.app # this is the Flask() instance

class TestBlock21BookmarkSearch(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()

    def test_search_by_substring(self):
        # seed two bookmarks
        b1 = "b21_alpha_one"
        b2 = "b21_beta_card"
        self.client.post("/bookmark", json={"bookmark": b1, "content": "first"})
        self.client.post("/bookmark", json={"bookmark": b2, "content": "second"})

        # 'alpha' should find b1
        r = self.client.get("/bookmark/search", query_string={"q": "alpha"})
        self.assertEqual(r.status_code, 200)
        hits = r.get_json()
        names = [h.get("bookmark") for h in hits]
        self.assertIn(b1, names)
        self.assertNotIn(b2, names)

if __name__ == "__main__":
    unittest.main()
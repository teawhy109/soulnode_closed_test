import unittest
import pathlib
import importlib.util

# Load root app.py explicitly
ROOT = pathlib.Path(__file__).resolve().parents[2]
APP_FILE = ROOT / "app.py"
spec = importlib.util.spec_from_file_location("app_module", str(APP_FILE))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

class TestBlock19BookmarkList(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_bookmark_list_returns_items_and_count(self):
        b1 = "b19_mark_one"
        b2 = "b19_mark_two"

        r1 = self.client.post("/bookmark", json={"bookmark": b1, "content": "first"})
        r2 = self.client.post("/bookmark", json={"bookmark": b2, "content": "second"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)

        r = self.client.get("/bookmark/list")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIsInstance(data, dict)
        self.assertIn("items", data)
        self.assertIn("count", data)
        self.assertIsInstance(data["items"], list)
        self.assertIsInstance(data["count"], int)
        self.assertGreaterEqual(data["count"], 2)

        names = " ".join([str(i.get("bookmark","")) for i in data["items"]])
        self.assertIn(b1, names)
        self.assertIn(b2, names)

if __name__ == "__main__":
    unittest.main()
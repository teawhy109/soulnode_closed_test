import unittest
import pathlib
import importlib.util
import json

# Load root app.py explicitly (avoid app/ package clash)
ROOT = pathlib.Path(__file__).resolve().parents[2]
APP_FILE = ROOT / "app.py"
spec = importlib.util.spec_from_file_location("app_module", str(APP_FILE))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

class TestBlock16MemoryList(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_list_returns_items_and_count(self):
        t1 = "block16_token_one"
        t2 = "block16_token_two"

        r1 = self.client.post("/save", json={"content": f"Test {t1}", "type": "private"})
        r2 = self.client.post("/save", json={"content": f"Test {t2}", "type": "private"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)

        r = self.client.get("/memory/list")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertIsInstance(data, dict)
        self.assertIn("items", data)
        self.assertIn("count", data)
        self.assertIsInstance(data["items"], list)
        self.assertIsInstance(data["count"], int)
        self.assertGreaterEqual(data["count"], 2)
        contents = " ".join([str(i.get("content", "")) for i in data["items"]])
        self.assertIn(t1, contents)
        self.assertIn(t2, contents)

if __name__ == "__main__":
    unittest.main()
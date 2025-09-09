import unittest
import json
import pathlib
import importlib.util

# Load root app.py explicitly (avoid app/ package name clash)
ROOT = pathlib.Path(__file__).resolve().parents[2]
APP_FILE = ROOT / "app.py"
spec = importlib.util.spec_from_file_location("app_module", str(APP_FILE))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

class TestBlock15MemoryRoundtrip(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_save_then_search(self):
        # Unique token for this test
        token = "block15_unique_phrase"

        # Save a memory (your /save already exists from earlier blocks)
        r1 = self.client.post(
            "/save",
            json={"content": f"Testing roundtrip {token}", "type": "private"}
        )
        self.assertEqual(r1.status_code, 200)

        # Search for it (memory_search requires user_id; adapter won’t over-filter)
        r2 = self.client.get(
            "/memory/search",
            query_string={"user_id": "test_user", "query": "block15_unique_phrase"}
        )
        self.assertEqual(r2.status_code, 200)
        data = r2.get_json()
        self.assertIsInstance(data, list)
        self.assertTrue(any(token in (m.get("content","")) for m in data))

if __name__ == "__main__":
    unittest.main()import unittest
import json
import pathlib
import importlib.util

# Load root app.py explicitly (avoid app/ package name clash)
ROOT = pathlib.Path(__file__).resolve().parents[2]
APP_FILE = ROOT / "app.py"
spec = importlib.util.spec_from_file_location("app_module", str(APP_FILE))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

class TestBlock15MemoryRoundtrip(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_save_then_search(self):
        # Unique token for this test
        token = "block15_unique_phrase"

        # Save a memory (your /save already exists from earlier blocks)
        r1 = self.client.post(
            "/save",
            json={"content": f"Testing roundtrip {token}", "type": "private"}
        )
        self.assertEqual(r1.status_code, 200)

        # Search for it (memory_search requires user_id; adapter won’t over-filter)
        r2 = self.client.get(
            "/memory/search",
            query_string={"user_id": "test_user", "query": "block15_unique_phrase"}
        )
        self.assertEqual(r2.status_code, 200)
        data = r2.get_json()
        self.assertIsInstance(data, list)
        self.assertTrue(any(token in (m.get("content","")) for m in data))

if __name__ == "__main__":
    unittest.main()
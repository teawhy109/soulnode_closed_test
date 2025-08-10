import unittest
import json
import os
import pathlib
import importlib.util

# --- Load the root-level app.py explicitly, avoiding the app/ package name clash ---
ROOT = pathlib.Path(__file__).resolve().parents[2] # .../soulnode_final_one
APP_FILE = ROOT / "app.py"

spec = importlib.util.spec_from_file_location("app_module", str(APP_FILE))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app
# -------------------------------------------------------------------------------

class TestBlock14MemorySearch(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_memory_search_not_present(self):
        # Query something that should not exist; endpoint must return 200 and a JSON list
        resp = self.client.get(
            "/memory/search",
            query_string={"user_id": "test_user", "query": "basketball"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        # Optional: many implementations return [] when no matches
        # If your endpoint behaves that way, keep this next assert; otherwise delete it.
        # self.assertEqual(len(data), 0)

if __name__ == "__main__":
    unittest.main()
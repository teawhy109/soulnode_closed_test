import unittest
import pathlib
import importlib.util
import json

# Load root app.py explicitly
ROOT = pathlib.Path(__file__).resolve().parents[2]
APP_FILE = ROOT / "app.py"
spec = importlib.util.spec_from_file_location("app_module", str(APP_FILE))
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

class TestBlock17MemoryDelete(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_delete_memory_by_id(self):
        # seed two memories
        r1 = self.client.post("/save", json={"content": "b17 keep me", "type": "private"})
        r2 = self.client.post("/save", json={"content": "b17 remove me", "type": "private"})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        id_to_delete = r2.get_json()["data"]["id"]

        # list before
        pre = self.client.get("/memory/list").get_json()
        pre_count = int(pre["count"])

        # delete target
        d = self.client.post("/memory/delete", json={"id": id_to_delete})
        self.assertEqual(d.status_code, 200)
        self.assertTrue(d.get_json().get("ok"))

        # list after
        post = self.client.get("/memory/list").get_json()
        self.assertEqual(int(post["count"]), pre_count - 1)
        joined = " ".join([i.get("content","") for i in post["items"]])
        self.assertNotIn("b17 remove me", joined)
        self.assertIn("b17 keep me", joined)

if __name__ == "__main__":
    unittest.main()
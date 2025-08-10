import os
import unittest
from importlib.machinery import SourceFileLoader

# Load app.py directly
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
APP_PATH = os.path.join(PROJECT_ROOT, "app.py")
app_module = SourceFileLoader("app_module", APP_PATH).load_module()
app = app_module.app


class TestBlock20BookmarkDelete(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_delete_bookmark_by_name(self):
        b1 = "b20_one"
        b2 = "b20_two"

        # create two bookmarks
        self.client.post("/bookmark", json={"bookmark": b1, "content": "first"})
        self.client.post("/bookmark", json={"bookmark": b2, "content": "second"})

        # count before
        before = self.client.get("/bookmark/list").get_json()
        pre_count = int(before.get("count", 0))

        # delete one
        resp = self.client.post("/bookmark/delete", json={"bookmark": b1})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get("status"), "ok")
        self.assertGreaterEqual(int(data.get("deleted", 0)), 1)

        # verify after
        after = self.client.get("/bookmark/list").get_json()
        self.assertEqual(int(after.get("count", 0)), max(pre_count - 1, 0))
        names = [i.get("bookmark") for i in after.get("items", [])]
        self.assertIn(b2, names)
        self.assertNotIn(b1, names)

    def test_delete_requires_name(self):
        r = self.client.post("/bookmark/delete", json={})
        self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()
import unittest
from pathlib import Path
from app import app as flask_app

class TestBlock22MomProfile(unittest.TestCase):
    def setUp(self):
        self.client = flask_app.test_client()
        # ensure a clean slate for each run
        root = Path(__file__).resolve().parents[2]
        self.mom_file = root / "mom_bookmarks.json"
        if self.mom_file.exists():
            self.mom_file.unlink()

    def test_profile_put_get_and_scoped_data(self):
        # add two mom-scoped bookmarks
        r1 = self.client.post("/mom/bookmark/add",
                              json={"bookmark": "appt", "content": "doctor visit"})
        self.assertEqual(r1.status_code, 200)

        r2 = self.client.post("/mom/bookmark/add",
                              json={"bookmark": "list", "content": "groceries"})
        self.assertEqual(r2.status_code, 200)

        # list & verify exactly the two we inserted
        resp = self.client.get("/mom/bookmark/list")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        names = [i.get("bookmark") for i in data.get("items", [])]

        self.assertIn("appt", names)
        self.assertIn("list", names)
        self.assertEqual(int(data.get("count", -1)), 2)

if __name__ == "__main__":
    unittest.main()
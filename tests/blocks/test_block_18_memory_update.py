import io
import json
from importlib.machinery import SourceFileLoader

# Load the Flask app module directly from app.py
APP_PATH = "app.py"
app_module = SourceFileLoader("app_module", APP_PATH).load_module()
app = app_module.app

class TestBlock18MemoryUpdate:
    def setup_method(self):
        self.client = app.test_client()

    def test_update_memory_by_id(self):
        # seed one memory (Block 10 returns id as STRING by contract)
        r = self.client.post("/save", json={"content": "b18 original text", "type": "private"})
        assert r.status_code == 200
        mem_id = r.get_json()["data"]["id"] # string id by Block 10 contract

        # verify present in list
        pre = self.client.get("/memory/list").get_json()
        joined_pre = " ".join([i.get("content","") for i in pre["items"]])
        assert "b18 original text" in joined_pre

        # update
        u = self.client.post("/memory/update", json={"id": mem_id, "content": "b18 edited text"})
        assert u.status_code == 200
        body = u.get_json()
        assert body.get("ok")

        # IMPORTANT: compare as strings to align with Block 10 contract
        assert str(int(body.get("id"))) == str(mem_id)

        # verify edited in list
        post = self.client.get("/memory/list").get_json()
        joined_post = " ".join([i.get("content","") for i in post["items"]])
        assert "b18 edited text" in joined_post
# tests/blocks/test_block_11_status_api.py
import importlib.util, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("root_app", ROOT / "app.py")
root_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(root_app)

app = root_app.app

def test_status_counts_and_mode(monkeypatch, tmp_path):
    # Point app storage to temp files so test is isolated
    mem_file = tmp_path / "SessionMemory.json"
    bm_file = tmp_path / "Bookmarks.json"
    monkeypatch.setattr(root_app, "_MEM_FILE", mem_file, raising=False)
    monkeypatch.setattr(root_app, "_BM_FILE", bm_file, raising=False)

    client = app.test_client()

    # Initial status should exist and counters be 0
    r = client.get("/status")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert isinstance(body["mode"], str)
    assert body["counters"]["memories"] == 0
    assert body["counters"]["bookmarks"] == 0

    # Add one memory and one bookmark
    r = client.post("/save", json={"content": "test mem", "type": "private"})
    assert r.status_code == 200
    r = client.post("/bookmark", json={"content": "test bm", "bookmark": "BM1"})
    assert r.status_code == 200

    # Status should reflect +1 each
    r = client.get("/status")
    body = r.get_json()
    assert body["counters"]["memories"] == 1
    assert body["counters"]["bookmarks"] == 1

import json
import pytest
import importlib.util
import pathlib

# Load the root-level app.py explicitly (bulletproof against import issues)
ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("root_app", ROOT / "app.py")
root_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(root_app)

app = root_app.app # Flask app object from app.py

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

def test_status_exposes_mode_and_counters(client):
    # Read initial status
    r = client.get("/status")
    assert r.status_code == 200
    s = r.get_json()
    assert s["ok"] is True
    assert isinstance(s["mode"], str)
    assert "memories" in s["counters"]
    assert "bookmarks" in s["counters"]
    pre_mems = int(s["counters"]["memories"])
    pre_bms = int(s["counters"]["bookmarks"])

    # Write one memory and one bookmark
    r1 = client.post("/save", json={"content": "block13-mem", "type": "private"})
    assert r1.status_code == 200
    r2 = client.post("/bookmark", json={"content": "block13-bm", "bookmark": "B13"})
    assert r2.status_code == 200

    # Verify counts incremented by exactly 1 each
    r3 = client.get("/status")
    assert r3.status_code == 200
    s2 = r3.get_json()
    assert int(s2["counters"]["memories"]) == pre_mems + 1
    assert int(s2["counters"]["bookmarks"]) == pre_bms + 1
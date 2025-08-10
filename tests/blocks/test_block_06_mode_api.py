# tests/blocks/test_block_06_mode_api.py

import importlib.util, pathlib, json

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("root_app", ROOT / "app.py")
root_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(root_app)

app = root_app.app

def test_get_mode_returns_current():
    client = app.test_client()
    r = client.get("/mode")
    assert r.status_code == 200
    body = r.get_json()
    assert "mode" in body
    assert isinstance(body["mode"], str)

def test_set_mode_valid_values_and_normalization():
    client = app.test_client()

    # accept soul
    r = client.post("/mode", json={"mode": "soul"})
    assert r.status_code == 200
    assert r.get_json()["mode"] == "soul"

    # accept legacy 'nobs' but normalize to 'no_bullshit'
    r = client.post("/mode", json={"mode": "nobs"})
    assert r.status_code == 200
    assert r.get_json()["mode"] == "no_bullshit"

def test_set_mode_rejects_invalid():
    client = app.test_client()

    # first, capture current
    current = client.get("/mode").get_json()["mode"]

    # now try an invalid mode
    r = client.post("/mode", json={"mode": "invalid-mode"})
    assert r.status_code == 400
    body = r.get_json()
    assert body["error"].startswith("invalid mode")

    # ensure it did not change
    after = client.get("/mode").get_json()["mode"]
    assert after == current
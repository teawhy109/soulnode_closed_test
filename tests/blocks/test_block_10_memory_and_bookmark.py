# tests/blocks/test_block_10_memory_and_bookmark.py
import importlib.util, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("root_app", ROOT / "app.py")
root_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(root_app)

app = root_app.app

def test_save_memory_happy_path():
    client = app.test_client()
    payload = {"content": "Ty once weighed 375 pounds and is now healing through fasting.", "type": "private"}
    r = client.post("/save", json=payload)
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("status") == "ok"
    assert isinstance(body.get("data", {}).get("id"), str)

def test_bookmark_happy_path():
    client = app.test_client()
    payload = {"content": "Kobe cried on the phone and said he wanted to come home.", "bookmark": "Kobe Call"}
    r = client.post("/bookmark", json=payload)
    assert r.status_code == 200
    body = r.get_json()
    assert body.get("status") == "ok"
    assert body.get("data", {}).get("bookmark") == "Kobe Call"

def test_save_requires_content():
    client = app.test_client()
    r = client.post("/save", json={"type": "private"})
    assert r.status_code == 400

def test_bookmark_requires_content_and_name():
    client = app.test_client()
    r = client.post("/bookmark", json={"content": ""})
    assert r.status_code == 400
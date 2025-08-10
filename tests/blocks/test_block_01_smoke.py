# tests/blocks/test_block_01_smoke.py
import importlib.util
import pathlib

# Load the root-level app.py explicitly to avoid the app/ package name collision
ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("root_app", ROOT / "app.py")
root_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(root_app)

app = root_app.app # Flask app object from app.py

def test_root_route_ok():
    client = app.test_client()
    r = client.get("/")
    assert r.status_code == 200
    assert r.data.decode("utf-8") == "SoulNode is active. Ready to receive your input."
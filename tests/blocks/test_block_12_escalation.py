import os
import sys
import json
import pytest
import importlib.util
import pathlib

# Force Python to see project root no matter where pytest runs
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Explicitly load app.py from the project root
app_path = pathlib.Path(__file__).parent.parent.parent / "app.py"
spec = importlib.util.spec_from_file_location("app", app_path)
app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app_module)
app = app_module.app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_escalation_happy_path(client):
    payload = {"message": "emergency situation override"}
    response = client.post("/escalate", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data is not None
# tests/blocks/test_block_08_process_text.py
import importlib.util, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("root_app", ROOT / "app.py")
root_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(root_app)

app = root_app.app
appmod = root_app

def test_process_text_happy_path(monkeypatch):
    # pass-through mapping
    monkeypatch.setattr(appmod, "get_response_for_prompt", lambda s: s, raising=True)
    # no-op speech
    monkeypatch.setattr(appmod, "speak_text", lambda t: None, raising=False)

    # fake OpenAI reply
    class _Choice: 
        def __init__(self, content): self.message = {"content": content}
    class _Resp:
        def __init__(self, content): self.choices = [_Choice(content)]
    def _fake_create(**kwargs): return _Resp("All green (text).")
    monkeypatch.setattr(appmod.openai.ChatCompletion, "create", staticmethod(_fake_create), raising=True)

    client = app.test_client()
    r = client.post("/process_text", json={"text": "what's my mission"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["response"] == "All green (text)."

def test_process_text_requires_text():
    client = app.test_client()
    r = client.post("/process_text", json={})
    assert r.status_code == 400
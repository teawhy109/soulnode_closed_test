# tests/blocks/test_block_02_process_audio.py
import importlib.util
import pathlib
import io

# Load the root-level app.py explicitly to avoid the app/ package name collision
ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("root_app", ROOT / "app.py")
root_app = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(root_app)

app = root_app.app
appmod = root_app # so monkeypatch targets the loaded module (app.py)

def test_process_audio_happy_path(monkeypatch):
    # Fake transcription + intent mapping
    monkeypatch.setattr(appmod, "transcribe_audio", lambda f: "what's my mission", raising=True)
    monkeypatch.setattr(appmod, "get_response_for_prompt", lambda s: s, raising=True)
    # No-op TTS
    monkeypatch.setattr(appmod, "speak_text", lambda text: None, raising=False)

    # Fake OpenAI response
    class _Choice:
        def __init__(self, content):
            self.message = {"content": content}
    class _Resp:
        def __init__(self, content):
            self.choices = [_Choice(content)]
    def _fake_create(**kwargs):
        return _Resp("All green.")

    monkeypatch.setattr(appmod.openai.ChatCompletion, "create", staticmethod(_fake_create), raising=True)

    client = app.test_client()
    data = {"audio": (io.BytesIO(b"fake-bytes"), "test.wav")}
    r = client.post("/process_audio", data=data, content_type="multipart/form-data")
    assert r.status_code == 200
    body = r.get_json()
    assert body["response"] == "All green."

def test_process_audio_requires_file():
    client = app.test_client()
    r = client.post("/process_audio", data={}, content_type="multipart/form-data")
    assert r.status_code == 400
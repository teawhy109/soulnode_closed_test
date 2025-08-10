# tests/blocks/test_block_07_tts_contract.py
# Verify voice.speak_text() uses the TTS generator without hitting real APIs.

import importlib

def test_speak_text_calls_elevenlabs_generator(monkeypatch, tmp_path):
    voice = importlib.import_module("voice")

    called = {"count": 0}

    def fake_generate_speech(text):
        called["count"] += 1
        return b"FAKE-WAV-DATA"

    # Patch whichever symbol exists
    patched = False
    if hasattr(voice, "generate_speech"):
        monkeypatch.setattr(voice, "generate_speech", fake_generate_speech, raising=True)
        patched = True
    elif hasattr(voice, "elevenlabs_voice") and hasattr(voice.elevenlabs_voice, "generate_speech"):
        monkeypatch.setattr(voice.elevenlabs_voice, "generate_speech", fake_generate_speech, raising=True)
        patched = True

    assert patched, "Could not find a generate_speech function to patch in voice module."

    # Try the version that writes to a file if supported
    out_file = tmp_path / "out.wav"
    try:
        ret = voice.speak_text("hello world", out_path=out_file)
        # File should exist and contain our fake bytes
        assert out_file.exists()
        with open(out_file, "rb") as f:
            assert f.read() == b"FAKE-WAV-DATA"
    except TypeError:
        # Fallback: function doesn't accept out_path; just call it
        ret = voice.speak_text("hello world")
        # If it returns bytes, verify them; if it returns None, that's ok—just make
        # sure our generator was called once.
        if ret is not None:
            assert ret == b"FAKE-WAV-DATA"

    # In all cases, our generator must have been called exactly once
    assert called["count"] == 1
# voice.py
# Unifies TTS so tests can monkeypatch cleanly.

from typing import Optional

# Try to import the real ElevenLabs adapter as a module so it can be patched
try:
    import elevenlabs_voice # your existing file with generate_speech(text)
    _real_generate = getattr(elevenlabs_voice, "generate_speech", None)
except Exception:
    elevenlabs_voice = None
    _real_generate = None


def generate_speech(text: str) -> bytes:
    """
    Core TTS entrypoint.
    In prod, proxies to elevenlabs_voice.generate_speech(text).
    In tests, this symbol is monkeypatched.
    """
    if _real_generate is not None:
        return _real_generate(text)
    # Safe fallback for tests/dev when adapter isn't available
    return b"FAKE-WAV-DATA"


def speak_text(text: str, out_path: Optional[str] = None):
    """
    Produce speech audio from text. If out_path is provided, write bytes to that file.
    Returns the audio bytes (or None if you prefer; tests tolerate both).
    """
    audio_bytes = generate_speech(text)
    if out_path:
        with open(out_path, "wb") as f:
            f.write(audio_bytes)
    return audio_bytes


# Keep a minimal stub so Block 2 can monkeypatch it cleanly
def transcribe_audio(audio_file):
    """
    Placeholder STT. Block 2 tests monkeypatch this.
    """
    return "transcribed text"
# tests/blocks/test_block_03_speech_to_text.py
# Contract check: the voice module exists and exposes the right callables.

import importlib

def test_voice_module_has_transcribe_and_speak():
    voice = importlib.import_module("voice")
    assert hasattr(voice, "transcribe_audio") and callable(voice.transcribe_audio)
    assert hasattr(voice, "speak_text") and callable(voice.speak_text)
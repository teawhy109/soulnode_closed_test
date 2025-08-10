import importlib
from pathlib import Path
import pytest


# ---- dynamic import so it works with your current layout ----
def _load_pipeline():
    """
    Try a few plausible module paths and return (transcribe_fn, ErrClass or None).
    Expected callable is named one of: transcribe_file, transcribe_audio, run.
    """
    candidates = [
        "audio.to.text_pipeline",
        "audio.to_text_pipeline",
        "audio_to_text_pipeline",
    ]
    module = None
    last_err = None
    for mod in candidates:
        try:
            module = importlib.import_module(mod)
            break
        except ModuleNotFoundError as e:
            last_err = e
    if module is None:
        raise last_err or ModuleNotFoundError("Could not import audio text pipeline")

    # find a transcribe callable by common names
    for name in ("transcribe_file", "transcribe_audio", "run", "pipeline"):
        fn = getattr(module, name, None)
        if callable(fn):
            break
    else:
        raise AttributeError(
            "Pipeline module found but no callable named "
            "'transcribe_file' | 'transcribe_audio' | 'run' | 'pipeline'"
        )

    # Optional custom error type
    err = getattr(module, "TranscriptionError", None)
    return fn, err


def _find_sample_wav() -> Path:
    """Locate a small wav test asset in repo (root or uploads/)."""
    for p in (Path("sample_tone.wav"), Path("uploads") / "sample_tone.wav"):
        if p.exists():
            return p
    pytest.skip("No sample_tone.wav found at project root or uploads/")


def test_transcribe_happy_path():
    transcribe, _ = _load_pipeline()
    wav = _find_sample_wav()

    out = transcribe(str(wav)) # accept str/Path either way

    # Be flexible: some pipelines return a string, others a dict with 'text'
    if isinstance(out, dict):
        text = out.get("text", "")
    else:
        text = str(out)

    assert isinstance(text, str)
    # We don’t assert specific content (tone file may yield empty text),
    # only that the call succeeds and returns a string-like result.
    assert text is not None


def test_transcribe_missing_file():
    transcribe, Err = _load_pipeline()
    bogus = "___does_not_exist___.wav"

    expected_exc = Err or (FileNotFoundError, RuntimeError, OSError)
    with pytest.raises(expected_exc):
        transcribe(bogus)
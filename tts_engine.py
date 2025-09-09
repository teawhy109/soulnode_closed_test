# tts_engine.py — ElevenLabs wrapper compatible with SoNo calls
import os, time
from pathlib import Path

try:
    import requests
except Exception:
    requests = None

VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
XI_KEY = os.getenv("ELEVENLABS_API_KEY", "").strip()

def is_configured() -> bool:
    return bool(VOICE_ID and XI_KEY and requests)

def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
    return p

def speak(text: str, out_dir: str | None = None, **kwargs) -> dict:
    """
    Compatible with app calls that pass out_dir=...
    Returns: {"ok": True, "audio_url": "/static/tts/<fname>.mp3"} or {"ok": False, "error": "..."}
    """
    if not is_configured():
        return {"ok": False, "error": "TTS not configured"}

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
        headers = {
            "xi-api-key": XI_KEY,
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.7},
        }
        r = requests.post(url, headers=headers, json=payload, timeout=60)
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}: {r.text[:180]}"}

        # Decide output directory
        if out_dir:
            outpath = Path(out_dir)
        else:
            outpath = Path("static/tts")
        _ensure_dir(outpath)

        fname = f"{int(time.time()*1000)}.mp3"
        (outpath / fname).write_bytes(r.content)

        # If saved under static/tts, expose via /static/tts
        # If a custom out_dir was provided, we still try to compute a web path if it's under static.
        if "static" in str(outpath).split(os.sep):
            # Find the part after 'static'
            parts = outpath.as_posix().split("static/", 1)
            web_prefix = "/static/" + (parts[1] + "/" if len(parts) > 1 and parts[1] else "")
            return {"ok": True, "audio_url": web_prefix + fname}

        # Fallback: return filesystem path if not under static
        return {"ok": True, "audio_url": str((outpath / fname).as_posix())}

    except Exception as e:
        return {"ok": False, "error": str(e)}

# Optional alternate names the app might probe for
def generate(text: str, **kwargs) -> dict:
    return speak(text, **kwargs)

def synthesize(text: str, **kwargs) -> dict:
    return speak(text, **kwargs)

def tts(text: str, **kwargs) -> dict:
    return speak(text, **kwargs)
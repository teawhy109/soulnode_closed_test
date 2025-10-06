# profiles.py
import json
from pathlib import Path
from typing import Dict, Any, Optional

def _coerce_facts(obj: Any) -> Dict[str, str]:
    """Return a lowercase-keyed facts dict no matter how it's provided."""
    if not obj:
        return {}
    # If someone stored a list of {key,value} objects, convert it.
    if isinstance(obj, list):
        out: Dict[str, str] = {}
        for it in obj:
            if not isinstance(it, dict):
                continue
            k = (it.get("key") or it.get("name") or it.get("rel") or "").strip().lower()
            v = (it.get("value") or it.get("val") or "").strip()
            if k:
                out[k] = v
        return out
    # Normal case: a dict of key->value
    if isinstance(obj, dict):
        return {str(k).strip().lower(): str(v).strip() for k, v in obj.items()}
    return {}

def load_profiles(dir_path: Path) -> Dict[str, Dict[str, Any]]:
    """Load mom/sono profile JSONs into a dict keyed by subject (lowercase)."""
    results: Dict[str, Dict[str, Any]] = {}
    for name in ("mom_profile.json", "sono_profile.json"):
        p = dir_path / name
        try:
            with p.open("r", encoding="utf-8") as f:
                obj = json.load(f)
            subj = (obj.get("subject") or name.split("_")[0]).strip().lower()
            display_names = obj.get("display_names") or [obj.get("display_name") or subj.title()]
            aliases = obj.get("aliases") or []
            facts = _coerce_facts(obj.get("facts"))
            results[subj] = {
                "subject": subj,
                "display_names": display_names,
                "aliases": aliases,
                "facts": facts,
            }
        except Exception as e:
            print(f"PROFILE load failed for {p}: {e}")
    return results

def profile_answer(sub: str, rel: str, profiles: Dict[str, Dict[str, Any]]) -> Optional[str]:
    """Return a profile fact if we have it, with a couple of natural fallbacks."""
    prof = profiles.get((sub or "").strip().lower())
    if not prof:
        return None
    facts = prof.get("facts", {})
    key = (rel or "").strip().lower()
    if key in facts:
        return str(facts[key])

    # simple aliases / fallbacks
    if key in ("name", "full name") and "full name" in facts:
        return facts["full name"]
    if key in ("birthplace", "birth place"):
        return facts.get("birthplace") or facts.get("birth place")
    if key in ("hometown", "where raised", "home"):
        return facts.get("hometown")
    if key in ("mom", "mother") and "mom" in facts:
        return facts["mom"]
    return None
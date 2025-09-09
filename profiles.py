# profiles.py
from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, Iterable
import json
import re

# ---- tiny normalizers ----
def _canon(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def _any_in(haystack: str, needles: Iterable[str]) -> bool:
    h = _canon(haystack)
    return any(n and n in h for n in (_canon(x) for x in needles))

# ---- loader ----
def load_profiles(base_path: Path) -> Dict[str, Any]:
    """
    Loads mom_profile.json from data/ and builds a small index:
      - subject key: canonical 'pam'
      - _names: set of all names/aliases for matching
    """
    mom_file = base_path / "mom_profile.json"
    with mom_file.open("r", encoding="utf-8") as f:
        mom = json.load(f)

    names = set()
    for n in [mom.get("subject", "")] + mom.get("display_names", []) + mom.get("aliases", []):
        if n:
            names.add(_canon(n))

    mom["_names"] = names
    # prefer display name for natural sentences
    mom["_pretty"] = (mom.get("display_names") or ["Pam"])[0]

    return {"pam": mom}

# ---- profile Q&A ----
_REL_MAP = {
    "full name": "full_name",
    "name": "full_name",
    "birthplace": "birthplace",
    "born": "birthplace",
    "where were you born": "birthplace",
    "where was she born": "birthplace",
    "where did you grow up": "hometown",
    "hometown": "hometown",
    "home town": "hometown",
    "grew up": "hometown",
}

def _pick_fact_key(rel: Optional[str], txt: str) -> Optional[str]:
    # 1) try explicit relation
    if rel:
        r = _canon(rel)
        if r in _REL_MAP:
            return _REL_MAP[r]
    # 2) try keywords in question text
    for k, v in _REL_MAP.items():
        if _any_in(txt, [k]):
            return v
    return None

def _match_profile(sub: Optional[str], txt: str, profiles: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Priority 1: subject parsed as 'pam'
    if _canon(sub) in ("pam", "pamlea", "pam leah", "ty's mom", "tys mom", "ty mom"):
        return profiles.get("pam")

    # Priority 2: mention in the raw text
    cand = profiles.get("pam")
    if not cand:
        return None
    if _any_in(txt, cand["_names"]):
        return cand

    return None

def profile_answer(sub: Optional[str], rel: Optional[str], txt: str) -> Optional[str]:
    """
    Return a natural sentence from profile facts, or None if not handled.
    """
    # Expect PROFILES to be created by app.py (we import lazily to avoid cycles)
    try:
        from app import PROFILES  # type: ignore
    except Exception:
        PROFILES = {}

    prof = _match_profile(sub, txt, PROFILES)
    if not prof:
        return None

    facts = prof.get("facts", {})
    key = _pick_fact_key(rel, txt)
    pretty = prof.get("_pretty", "Pam")

    if not key:
        return None

    val = facts.get(key)
    if not val:
        return None

    if key == "full_name":
        return f"{val} is {pretty}'s full name."
    if key == "birthplace":
        return f"{pretty} was born in {val}."
    if key == "hometown":
        return f"{pretty} grew up in {val}."

    # default sentence
    return f"{pretty}'s {key.replace('_',' ')} is {val}."
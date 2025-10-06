# normalize.py — tiny, safe, no top-level code

import re
import unicodedata as ud

# --- helpers -------------------------------------------------

def _squash(s: str) -> str:
    """strip + collapse internal whitespace to single spaces"""
    return re.sub(r"\s+", " ", s.strip())

def _basic(s: str) -> str:
    """lowercase, strip accents"""
    s = ud.normalize("NFKD", s)
    s = "".join(ch for ch in s if not ud.combining(ch))
    return _squash(s.lower())

# Common alias fixes (Whisper variants etc.)
_ALIAS = {
    "pam leah": "pamlea",
    "pam-leah": "pamlea",
    "pamlea": "pamlea", # idempotent
    "pamlea h": "pamlea", # defensive
}

def _alias_key(s: str) -> str:
    k = _basic(s)
    return _ALIAS.get(k, k)

# --- public API ----------------------------------------------

def canonical_subject(text: str) -> str:
    """
    Turn subjects like:
      'Pam Leah', 'Pam-Leah', 'pamlea h'
    into a stable key 'pamlea'
    """
    return _alias_key(text)

def canonical_relation(text: str) -> str:
    """
    Map varied phrasings to compact keys:
      "what's ty's favorite nfl team" -> "nfl_team"
      "favorite nba team" -> "nba_team"
      "hometown" -> "hometown"
      "mom" -> "mother"
    """
    t = _basic(text)
    # light intent-style matching
    if "nfl" in t and "team" in t:
        return "nfl_team"
    if ("nba" in t or "basketball" in t) and "team" in t:
        return "nba_team"
    if "hometown" in t or ("home" in t and "town" in t):
        return "hometown"
    if t in {"mom", "mother", "who is ty's mom", "who is tys mom"}:
        return "mother"
    return t

def clean_value(raw: str | None) -> str:
    """
    Gentle post-process for values we store/speak:
      - keep as-is if None -> ""
      - trim quotes
      - drop one trailing period for short answers
    """
    if raw is None:
        return ""
    v = _squash(str(raw))
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1].strip()
    if len(v) <= 64 and v.endswith("."):
        v = v[:-1].strip()
    return v
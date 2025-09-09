# rickey_qna.py
# -------------------------------------------------------------------
# Deterministic Q&A for Rickey (Big Rick) Butler.
# Exposes: _match_rickey_qna(text: str) -> Optional[str]
# Also exports alias `rickey_qna` for convenience.
# -------------------------------------------------------------------

from __future__ import annotations
from typing import Optional, Iterable, Dict, List
import re

# ---- Name normalization ------------------------------------------------
# Map common variants to the canonical "rickey"
# rickey_qna.py
from typing import Optional, Iterable
import re

_RULES = {
    "who_is_rickey": {
        "patterns": [r"\b(who\s+is|who\s+was)\s+(rickey|rickey|big\s+rick)\b"],
        "answer": "Rickey Butler (spelled Rickey) — Pam’s husband, Ty’s dad — worked heavy labor (Bethlehem Brick), long commutes; family-first, dependable, funny, and protective."
    },
    # add more patterns/answers here…
}

_ALIAS_RULES = [
    (r"\bricky\b", "rickey"),
    (r"\brickie\b", "rickey"),
    (r"\bbig\s*r(i|e)ck\b", "rickey"),
]

def _normalize(text: str) -> str:
    out = text or ""
    for pat, repl in _ALIAS_RULES:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out

def _match_rickey_qna(text: str) -> Optional[str]:
    if not isinstance(text, str) or not text.strip():
        return None
    t = _normalize(text)
    for rule in _RULES.values():
        for pat in rule.get("patterns", []):
            if re.search(pat, t, flags=re.IGNORECASE):
                return rule.get("answer")
    return None

# ---- Hard facts / phrases we want to return verbatim -------------------
# Tweak these to your family’s truths.
_FACTS: Dict[str, str] = {
    "who_is": (
        "Rickey Butler (often called Big Rick) — Ty’s father and Pam’s husband. "
        "A steady, hard-working man, family-first, and the heart of the household."
    ),
    "work": (
        "Rickey worked heavy labor — long commutes, tough shifts. "
        "He put in time at Bethlehem (brick/steel/yard) to keep the family stable."
    ),
    "promise_ty": (
        "He told Ty, plain and simple: “You’ll always be good.” "
        "That promise — to have his son’s back — became a core family anchor."
    ),
    "husband_father": (
        "A devoted husband to Pam and a caring father. Not flashy — reliable, present, and protective."
    ),
    "memory_pam": (
        "Pam’s favorite memory: an anniversary at the casino. "
        "She changed into a teddy; Rickey lifted and held her tight — made her feel beautiful."
    ),
}

# ---- Pattern rules -----------------------------------------------------
# Each key maps to a set of regexes; the first hit returns the associated fact text.
_RULES: Dict[str, Dict[str, Iterable[str]]] = {
    "who_is": {
        "patterns": [
            r"\bwho\s+is\s+(rickey|rickey butler)\b",
            r"\bwho\s+was\s+(rickey|rickey butler)\b",
            r"\bwho\s+is\s+pam('?s)?\s+husband\b",
            r"\bwho\s+is\s+ty('?s)?\s+dad\b",
        ]
    },
    "work": {
        "patterns": [
            r"\bwhat\s+did\s+(rickey|rickey butler)\s+do\s+for\s+work\b",
            r"\bwhere\s+did\s+(rickey|rickey butler)\s+work\b",
            r"\b(tell|talk)\s+me\s+about\s+(rickey|rickey butler)('s)?\s+work\b",
            r"\bwhat\s+job\s+did\s+(rickey|rickey butler)\s+have\b",
        ]
    },
    "promise_ty": {
        "patterns": [
            r"\bwhat\s+did\s+(rickey|rickey butler)\s+promise\s+ty\b",
            r"\bwhat\s+promise\s+did\s+(rickey|rickey butler)\s+make\s+to\s+ty\b",
        ]
    },
    "husband_father": {
        "patterns": [
            r"\bwhat\s+kind\s+of\s+(husband|father)\s+was\s+(rickey|rickey butler)\b",
            r"\bdescribe\s+(rickey|rickey butler)\s+as\s+(a\s+)?(dad|father|husband)\b",
        ]
    },
    "memory_pam": {
        "patterns": [
            r"\b(pam|pamlea)\b.*\bfavorite\b.*\bmemory\b.*\b(rickey|rickey butler)\b",
            r"\bwhat\s+was\s+pam('?s)?\s+favorite\s+memory\s+of\s+(rickey|rickey butler)\b",
        ]
    },
}

# Optional fuzzy fallback: key words that strongly imply a rule if no pattern matched.
_FUZZY_INDEX: List[tuple[Iterable[str], str]] = [
    (("who", "rickey"), "who_is"),
    (("work", "rickey"), "work"),
    (("promise", "ty", "rickey"), "promise_ty"),
    (("husband", "rickey"), "husband_father"),
    (("favorite", "memory", "pam", "rickey"), "memory_pam"),
]

def _keywords_hit(norm: str, words: Iterable[str]) -> bool:
    return all(w in norm for w in words)

# ---- Public API --------------------------------------------------------
def _match_rickey_qna(text: str) -> Optional[str]:
    """
    Return a Rickey-specific answer if we can confidently match, else None.
    """
    if not isinstance(text, str) or not text.strip():
        return None

    norm = _normalize(text)

    # 1) Exact pattern matches
    for key, rule in _RULES.items():
        for pat in rule.get("patterns", []):
            if re.search(pat, norm, flags=re.IGNORECASE):
                return _FACTS[key]

    # 2) Lightweight fuzzy keywords (order-insensitive “contains all”)
    for words, key in _FUZZY_INDEX:
        if _keywords_hit(norm, words):
            return _FACTS[key]

    # 3) No confident match
    return None

# Export a friendly alias so app.py can import either name safely
rickey_qna = _match_rickey_qna
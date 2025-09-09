# pamlea_qna.py
# Deterministic Q&A for Pam (Pamela Louise Henderson Butler)

from __future__ import annotations
import re
from typing import Optional, Iterable

# --- aliases to normalize phrasing ---
_ALIAS_RULES = [
    (r"\bpam butler\b", "pamlea butler"),
    (r"\bpamela\b", "pamlea"),
    (r"\bpam\b", "pamlea"),
    (r"\bwho is ty'?s mom\b", "who is pamlea"),
]

def _normalize(text: str) -> str:
    out = text
    for pat, repl in _ALIAS_RULES:
        out = re.sub(pat, repl, out, flags=re.IGNORECASE)
    return out.strip()

# --- facts pulled from your interview ---
FULL_NAME = "Pamela Louise Henderson (later Pam Butler)"
BIRTHPLACE = "Midland, Texas"
BIRTHDATE = "June 4, 1954"
BIRTH_DETAILS = f"{BIRTHPLACE} on {BIRTHDATE}, at her Aunt Amy’s house"
SPOUSE = "Rickey (Big Rick) Butler"
RAISED_BY = "Her grandmother, Mamie “Big Mama” Sorrells"
CHILDREN = "Jay, Ty (Tyease), and Asia"
EARLY_PLACES = "Midland (TX), Denver (CO), and Los Angeles (CA)"

# Favorite memory phrasing from the story you gave:
FAVE_MEMORY_RICKEY = (
    "On an anniversary, Rickey surprised her with a casino hotel room. "
    "She came out wearing a teddy, and he hugged and picked her up—she felt beautiful."
)

# --- rules: patterns -> answers ---
_RULES = {
    "who": {
        "patterns": [
            r"\bwho\s+is\s+pamlea\b",
            r"\bwho\s+is\s+pamlea\s+butler\b",
            r"\bwho\s+is\s+ty'?s\s+mom\b",
        ],
        "reply": f"Pam is {FULL_NAME}. She’s Ty’s mother and is married to {SPOUSE}."
    },
    "full_name": {
        "patterns": [
            r"\bwhat\s+is\s+pamlea'?s\s+full\s+name\b",
            r"\bpamlea'?s\s+full\s+name\b",
        ],
        "reply": FULL_NAME
    },
    "born_where": {
        "patterns": [
            r"\bwhere\s+was\s+pamlea\s+born\b",
            r"\bwhat\s+city\s+was\s+pamlea\s+born\b",
        ],
        "reply": BIRTHPLACE
    },
    "born_when": {
        "patterns": [
            r"\bwhen\s+was\s+pamlea\s+born\b",
            r"\bpamlea'?s\s+birthday\b",
            r"\bwhat\s+is\s+pamlea'?s\s+birth(day|date)\b",
        ],
        "reply": BIRTHDATE
    },
    "birth_details": {
        "patterns": [
            r"\bwhere\s+and\s+when\s+was\s+pamlea\s+born\b",
            r"\btell\s+me\s+about\s+pamlea'?s\s+birth\b",
        ],
        "reply": BIRTH_DETAILS
    },
    "raised_by": {
        "patterns": [
            r"\bwho\s+raised\s+pamlea\b",
            r"\bpamlea\s+was\s+raised\s+by\b",
        ],
        "reply": RAISED_BY
    },
    "kids": {
        "patterns": [
            r"\bwho\s+are\s+pamlea'?s\s+children\b",
            r"\bhow\s+many\s+kids\s+does\s+pamlea\s+have\b",
        ],
        "reply": CHILDREN
    },
    "lived": {
        "patterns": [
            r"\bwhere\s+did\s+pamlea\s+(grow\s+up|live)\b",
            r"\bplaces\s+pamlea\s+lived\b",
        ],
        "reply": f"She lived in {EARLY_PLACES}."
    },
    "husband": {
        "patterns": [
            r"\bwho\s+is\s+pamlea'?s\s+husband\b",
            r"\bpamlea\s+married\b",
        ],
        "reply": SPOUSE
    },
    "fav_memory_rickey": {
        "patterns": [
            r"\b(pam|pamlea)\b.*\bfavorite\b.*\b(memory|moment)\b.*\brickey\b",
            r"\bwhat\s+was\s+pamlea'?s\s+favorite\s+memory\s+of\s+rickey\b",
        ],
        "reply": FAVE_MEMORY_RICKEY
    },
}

# --- public API (match function) ---
def _match_pamlea_qna(text: str) -> Optional[str]:
    """Return a Pam-specific answer if we can confidently match, else None."""
    if not isinstance(text, str) or not text.strip():
        return None
    norm = _normalize(text)
    for rule in _RULES.values():
        pats: Iterable[str] = rule.get("patterns", [])
        for pat in pats:
            if re.search(pat, norm, flags=re.IGNORECASE):
                return rule["reply"]
    return None
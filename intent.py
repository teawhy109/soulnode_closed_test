# intent.py
# SoNo intent parser: teach / update / forget / ask + speech-fragment expansion
import re, unicodedata
from typing import Tuple, Optional
from normalize import canonical_subject, canonical_relation, clean_value, _squash

# --- utils --------------------------------------------------------------------

_APOS = ("'", "’", "ʼ", "‘", "‛", "＇")

def _preclean(s: str) -> str:
    """Normalize Unicode, unify apostrophes/quotes, trim noise."""
    s = unicodedata.normalize("NFKC", s or "")
    for a in _APOS:
        s = s.replace(a, "'")
    s = (s.replace("“", '"').replace("”", '"').replace("…", "..."))
    return s.strip()

def _postprocess(sub: str, rel: str, obj: Optional[str]) -> Tuple[str,str,Optional[str]]:
    """
    Canonicalize subject & relation; reshape favorite-* patterns; clean object.
    """
    csub = canonical_subject(sub)
    crel = canonical_relation(rel)

    # If user typed "favorite color is royal blue" but parser captured "favorite" as rel
    if obj:
        sq = _squash(obj)
        m = re.match(r"^(?:is\s+)?(color|colour|drink|song|show|movie|team|food|sport)\s+(?:is\s+)?(.+)$", sq)
        if crel == "favorite" and m:
            noun = m.group(1)
            if noun == "colour": noun = "color"
            crel = f"favorite {noun}"
            obj = m.group(2)

    return csub, crel, (clean_value(obj) if obj is not None else None)

# --- speech fragment expansion (95→100) ---------------------------------------
# e.g., "ty mom" → ask(ty, mother), "ivy fav color" → ask(ivy, favorite color)
_FRAG_REL_MAP = {
    "mom":"mother", "mother":"mother",
    "dad":"father", "father":"father",
    "fav":"favorite", "fave":"favorite", "favorite":"favorite",
    "color":"favorite color", "colour":"favorite color",
    "coffee":"coffee order", "coffeeorder":"coffee order",
    "sport":"favorite sport", "team":"favorite team",
    "drink":"favorite drink", "movie":"favorite movie",
    "song":"favorite song", "show":"favorite show", "food":"favorite food"
}

def _try_fragment_to_ask(t: str):
    """
    Turn short speech fragments into an ask.
    Only triggers for <= 4 tokens and no explicit teach/update/forget verbs.
    """
    sq = _squash(t)
    if not sq:
        return None
    if any(w in sq for w in ("remember","update","change","forget","import","export")):
        return None

    toks = sq.split()
    if not (1 <= len(toks) <= 4):
        return None

    subj = toks[0]
    # normalize possessive: ivy's -> ivy
    if subj.endswith("'s"):
        subj = subj[:-2]

    rel_tokens = toks[1:]
    if not rel_tokens:
        # single-token like "mom" is ambiguous (no subject) — skip
        return None

    mapped = []
    for rt in rel_tokens:
        rt2 = _FRAG_REL_MAP.get(rt, rt)
        mapped.append(rt2)
    rel_guess = " ".join(mapped).strip()
    # collapse common two-token combos e.g. "fav color"
    rel_guess = _FRAG_REL_MAP.get(rel_guess, rel_guess)

    sub, rel, _ = _postprocess(subj, rel_guess, None)
    return ("ask", sub, rel, None)

# --- patterns -----------------------------------------------------------------
# Accept both straight and curly apostrophes in possessives:
# (?:['’ʼ]s)? and allow them in subject class: [\w'’ʼ ]
APOS_CLASS = "'’ʼ"

TEACH_PATTERNS = [
    re.compile(rf"""
        ^(?:\s*(?:hey\s+)?sono[,!\s]*)?
        remember\s+that\s+
        (?P<sub>[\w{APOS_CLASS} ]+?)(?:['’ʼ]s)?\s+
        (?:(?P<fav>(?:fav|fave|favorite|favourite))\s+)?(?P<rel>[\w ]+?)\s+
        (?:is|=)\s+(?P<obj>.+)$
    """, re.I | re.X),
    re.compile(rf"""
        ^(?:\s*(?:hey\s+)?sono[,!\s]*)?
        remember\s+
        (?P<sub>[\w{APOS_CLASS} ]+?)(?:['’ʼ]s)?\s+(?P<rel>[\w ]+?)\s+(?:is|=)\s+(?P<obj>.+)$
    """, re.I | re.X),
]

UPDATE_PATTERN = re.compile(rf"""
    ^(?:\s*(?:hey\s+)?sono[,!\s]*)?
    (?:update|change)\s+
    (?P<sub>[\w{APOS_CLASS} ]+?)(?:['’ʼ]s)?\s+(?P<rel>[\w ]+?)\s+(?:to|=)\s+(?P<obj>.+)$
""", re.I | re.X)

FORGET_PATTERN = re.compile(rf"""
    ^(?:\s*(?:hey\s+)?sono[,!\s]*)?
    forget\s+(?P<sub>[\w{APOS_CLASS} ]+?)(?:['’ʼ]s)?\s+(?P<rel>[\w ]+?)\s*\.?$
""", re.I | re.X)

ASK_PATTERNS = [
    re.compile(rf"""^who(?:'s|\s+is)\s+(?P<sub>[\w{APOS_CLASS} ]+?)(?:['’ʼ]s)?\s+(?P<rel>mom|mother)\s*\??$""", re.I | re.X),
    re.compile(rf"""
        ^what(?:'s|\s+is)\s+(?P<sub>[\w{APOS_CLASS} ]+?)(?:['’ʼ]s)?\s+
        (?:(?P<fav>(?:fav|fave|favorite|favourite))\s+)?(?P<rel>[\w ]+?)\s*\??$
    """, re.I | re.X),
    re.compile(rf"""^which\s+(?:is\s+)?(?P<sub>[\w{APOS_CLASS} ]+?)(?:['’ʼ]s)?\s+(?P<rel>[\w ]+?)\s*\??$""", re.I | re.X),
    re.compile(rf"""^(?:tell\s+me|remind\s+me|what)\s+.*?(?P<sub>[\w{APOS_CLASS} ]+?)(?:['’ʼ]s)?\s+(?P<rel>[\w ]+?)\s*\??$""", re.I | re.X),
]

# --- main entry ---------------------------------------------------------------

def parse_intent(text: str):
    t = _preclean(text)

    # 1) Try speech fragment expansion first
    frag = _try_fragment_to_ask(t)
    if frag:
        return frag

    # 2) Teach
    for pat in TEACH_PATTERNS:
        m = pat.match(t)
        if m:
            sub = m.group("sub")
            rel_raw = (m.group("rel") or "").strip()
            fav = (m.groupdict().get("fav") or "").strip()
            rel = f"{fav} {rel_raw}".strip() if fav else rel_raw
            obj = m.group("obj")
            sub, rel, obj = _postprocess(sub, rel, obj)
            return ("teach", sub, rel, obj)

    # 3) Update
    m = UPDATE_PATTERN.match(t)
    if m:
        sub, rel, obj = m.group("sub"), m.group("rel"), m.group("obj")
        sub, rel, obj = _postprocess(sub, rel, obj)
        return ("update", sub, rel, obj)

    # 4) Forget
    m = FORGET_PATTERN.match(t)
    if m:
        sub, rel = m.group("sub"), m.group("rel")
        sub, rel, _ = _postprocess(sub, rel, None)
        return ("forget", sub, rel, None)

    # 5) Ask
    for pat in ASK_PATTERNS:
        m = pat.match(t)
        if m:
            sub = m.group("sub")
            fav = (m.groupdict().get("fav") or "").strip()
            rel_raw = (m.group("rel") or "").strip()
            rel = f"{fav} {rel_raw}".strip() if fav else rel_raw
            sub, rel, _ = _postprocess(sub, rel, None)
            return ("ask", sub, rel, None)

    # 6) Unknown
    return ("unknown", "", "", None)
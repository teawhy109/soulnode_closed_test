# app.py — SoNo server (relaxed Q&A + aliases + multi-word relations + PETS FIX)
# Fixes:
# - Recognizes possessive-only questions like "Pam's birthday", "Pam's favorite restaurants"
# - Queries memory using lowercase subject/rel variants to match your stored keys
# - Keeps pets consolidation and everything else you had working

import os, re, json, logging, requests
from functools import lru_cache
from typing import Optional, Tuple, Any
from flask import Flask, request, jsonify, render_template

# ---- Env (optional LLM rewriter) --------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

OPENAI_API_KEY = (os.getenv("OPENAI_API_KEY") or "").strip()

# ---- Logging / Validation ----------------------------------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sono")

MAX_INPUT_LEN = 500 # guard against very long inputs

def validate_input_str(s: str, max_len: int = 160) -> bool:
    return isinstance(s, str) and 0 < len(s.strip()) <= max_len

# ---- Memory layer ------------------------------------------------------------
try:
    from soulnode_memory import SoulNodeMemory
except Exception as e:
    raise RuntimeError(f"Could not import SoulNodeMemory: {e}")

app = Flask(__name__)
memory = SoulNodeMemory()

# =============================================================================
# Text Normalization + Aliases
# =============================================================================

def _clean_text(t: str) -> str:
    if not t:
        return ""
    t = t.replace("’", "'").replace("‘", "'").replace("`", "'")
    t = t.replace("“", '"').replace("”", '"')
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _loose_possessives(t: str) -> str:
    """
    Treat 'Pams husband' like 'Pam's husband' (light-touch).
    """
    rel_words = r"(husband|wife|father|mother|son|daughter|child|children|kid|kids|sibling|siblings|brother|brothers|sister|sisters|mission|purpose|goal|spouse|birthday|birthdate|birth date|birth place|birthplace|raised by|restaurants|favorite restaurants|favorite foods|schools attended|full name|name|pet|pets)"
    def fix(m):
        return f"{m.group(1)}'s {m.group(2)}"
    pattern = re.compile(r"\b([A-Za-z]+)s\s+" + rel_words + r"\b", re.I)
    return pattern.sub(fix, t)

def _titlecase_name(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s

# ---- Subject Aliases (any → canonical seed) ---------------------------------
SUBJECT_ALIASES = {
    # Pam
    "pam": "Pam",
    "pamela": "Pam",
    "pamela butler": "Pam",
    "pam butler": "Pam",
    "pam's": "Pam",
    "pams": "Pam",
    # Rickey
    "rickey": "Rickey",
    "ricky": "Rickey",
    "rickey butler": "Rickey",
    "ricky butler": "Rickey",
    # Family nicknames (expandable)
    "big mama": "Mamie Sorrell",
    "mama lil": "Lillian Miller",
}

def _canon_subject(s: str) -> str:
    k = (s or "").strip().lower()
    return SUBJECT_ALIASES.get(k, _titlecase_name((s or "").strip()))

def _subject_candidates(subj: str):
    """
    Return many spellings/cases so lookups hit your stored lowercase keys.
    """
    s = (subj or "").strip()
    low = s.lower()
    cands = {s, s.lower(), _titlecase_name(s)}
    # Pam cluster
    if "pam" in low or "pamela" in low:
        cands.update({
            "Pam", "pam",
            "Pamela", "pamela",
            "Pam Butler", "pam butler",
            "Pamela Butler", "pamela butler"
        })
    # Rickey cluster (include Ricky spelling)
    if "rick" in low:
        cands.update({
            "Rickey", "rickey",
            "Ricky", "ricky",
            "Rickey Butler", "rickey butler",
            "Ricky Butler", "ricky butler"
        })
    return list(cands)

# ---- Relation synonyms → canonical keys -------------------------------------
def _normalize_synonym(rel_raw: str) -> str:
    r = re.sub(r"\s+", " ", (rel_raw or "").lower().strip())
    # group / family
    if r in {"child","kid","kids","children"}: return "children"
    if r in {"brothers","sisters","sibling","siblings"}: return "siblings"
    if r in {"spouse"}: return "husband"
    # birth
    if r in {"dob","date of birth","birth date","birthdate","birthday"}: return "birthday"
    if r in {"born","from","birth place","place of birth","birthplace"}: return "birthplace"
    # details
    if r in {"fullname","full name","name"}: return "full name"
    if r in {"raised","raisedby","raised by"}: return "raised by"
    if r in {"restaurants","favorite restaurants","favorite_restaurants"}: return "favorite restaurants"
    if r in {"foods","favorite foods","favorite_meals","meals"}: return "favorite foods"
    if r in {"schools","schools attended","education","educated at"}: return "schools attended"
    if r in {"pet","pets","animals"}: return "pet"
    return r

# =============================================================================
# Assertion Parsing (Natural-language SAVE)
# =============================================================================

ASSERT_PATTERNS = [
    # "Pam's husband is Rickey"
    re.compile(
        r"^\s*(?P<subject>[^?]+?)'s\s+(?P<relation>[A-Za-z\- ]+?)\s+is\s+(?P<object>[^.?!]+)\s*[.?!]?\s*$",
        re.I,
    ),
    # "Rickey is (the) husband of Pam"
    re.compile(
        r"^\s*(?P<object>[^?]+?)\s+is\s+(?:the\s+)?(?P<relation>[A-Za-z\- ]+?)\s+of\s+(?P<subject>[^.?!]+)\s*[.?!]?\s*$",
        re.I,
    ),
    # "Pam has children Ty Aja and Jade" / "Pam's favorite restaurants are ..."
    re.compile(
        r"^\s*(?P<subject>[^?]+?)\s+has\s+(?P<relation>[A-Za-z\- ]+?)\s+(?P<object>[^.?!]+)\s*[.?!]?\s*$",
        re.I,
    ),
]

def _split_names_loose(s: str):
    """
    Split loose lists like "Ty, Aja and Jade" / "El Torito's, Chili's and Carter's BBQ"
    """
    s2 = re.sub(r"\s*(?:,|and|&)\s*", ",", s, flags=re.I)
    parts = [p.strip() for p in s2.split(",") if p.strip()]
    if len(parts) == 1:
        parts = [p for p in re.split(r"\s+", parts[0]) if p]
    return [_titlecase_name(p) for p in parts]

def parse_assertion(text: str):
    t = _loose_possessives(_clean_text(text))
    if not t:
        return None
    for pat in ASSERT_PATTERNS:
        m = pat.match(t)
        if m:
            subj = _canon_subject(m.group("subject").strip(" '\""))
            rel = _normalize_synonym(m.group("relation"))
            obj_raw = m.group("object").strip(" '\"")
            if rel in {"children","siblings","favorite foods","favorite restaurants","schools attended","raised by","pet"}:
                obj = _split_names_loose(obj_raw)
            else:
                obj = _titlecase_name(obj_raw)
            return (subj, rel, obj)
    return None

# =============================================================================
# Question Parsing (LOOKUP) — relaxed, multi-word, yes/no forms
# =============================================================================

QUESTION_PATTERNS = [
    # 0) exact: "who raised pam" / "who primarily raised pam"
    re.compile(r"^\s*who\s+(?:primarily\s+)?raised\s+(.+?)\b.*$", re.I),

    # 0b) possessive-only question: "Pam's <relation>" (NEW)
    re.compile(r"^\s*([A-Za-z][\w \-]+?)'s\s+([\w\- ]{1,30})\b.*$", re.I),

    # 1) who/what/where with possessive ("who is pam's husband" etc.)
    re.compile(r"^\s*who\s+(?:is|are|was|were)\s+(.+?)'s\s+([\w\- ]{1,30})\b.*$", re.I),
    re.compile(r"^\s*what\s+(?:is|are|was|were)\s+(.+?)'s\s+([\w\- ]{1,30})\b.*$", re.I),
    re.compile(r"^\s*where\s+(?:is|was)\s+(.+?)'s\s+([\w\- ]{1,30})\b.*$", re.I),

    # 2) terse forms: "pam siblings", "pam birthplace", "rickey schools attended"
    re.compile(r"^\s*([\w \-]+?)\s+([\w\- ]{1,30})\b.*$", re.I),

    # 3) where-born forms: "where was pam born", "where is rickey from"
    re.compile(r"^\s*where\s+(?:was|is)\s+(.+?)\s+(?:born|from)\b.*$", re.I),

    # 4) did/does/has… forms (yes/no → convert to canonical relation)
    re.compile(r"^\s*(?:did|does|has|have)\s+(.+?)\s+(?:have|has)\s+(?:a|any\s+)?(pets?|children|kids|siblings?)\b.*$", re.I),
    re.compile(r"^\s*(?:did|does|has|have)\s+(.+?)\s+(?:have|has)\s+(?:a|any\s+)?(husband|spouse)\b.*$", re.I),
]

def _natural_alias(text: str) -> Optional[Tuple[str,str]]:
    """
    Soft rewrite common natural questions to (subject, relation).
    """
    x = _loose_possessives(_clean_text(text))
    xl = x.lower()

    # birthday
    m = re.match(r"^\s*when\s+(?:is|was)\s+(.+?)'s\s+(birthday|birth\s*date|birthdate|date\s+of\s+birth|dob)\b.*$", xl, re.I)
    if m: return (_canon_subject(m.group(1)), "birthday")

    # birthplace
    m = re.match(r"^\s*where\s+(?:is|was)\s+(.+?)\s+born\b.*$", xl, re.I)
    if m: return (_canon_subject(m.group(1)), "birthplace")

    # who raised <subject>
    m = re.match(r"^\s*who\s+(?:primarily\s+)?raised\s+(.+?)\b.*$", xl, re.I)
    if m: return (_canon_subject(m.group(1)), "raised by")

    # favorites
    m = re.match(r"^\s*what\s+(?:are|were)\s+(.+?)'s\s+favorite\s+restaurants?\b.*$", xl, re.I)
    if m: return (_canon_subject(m.group(1)), "favorite restaurants")
    m = re.match(r"^\s*what\s+(?:are|were)\s+(.+?)'s\s+favorite\s+(?:foods?|meals?)\b.*$", xl, re.I)
    if m: return (_canon_subject(m.group(1)), "favorite foods")

    # spouse
    m = re.match(r"^\s*who\s+(?:is|was)\s+(.+?)'s\s+(husband|spouse)\b.*$", xl, re.I)
    if m: return (_canon_subject(m.group(1)), "husband")

    # did/does have X
    m = re.match(r"^\s*(?:did|does|has|have)\s+(.+?)\s+(?:have|has)\s+(?:a|any\s+)?(pets?|children|kids|siblings?)\b.*$", xl, re.I)
    if m: return (_canon_subject(m.group(1)), _normalize_synonym(m.group(2)))

    return None

def parse_subject_relation(text: str) -> Optional[Tuple[str, str]]:
    t = _loose_possessives(_clean_text(text))
    for pat in QUESTION_PATTERNS:
        m = pat.match(t)
        if not m:
            continue

        p = pat.pattern

        # 0) who raised <subject>
        if p.startswith("^\\s*who\\s+(?:primarily\\s+)?raised\\s+"):
            subj_raw = m.group(1)
            return (_canon_subject(subj_raw.strip("'\" ")), "raised by")

        # 0b) "X's Y" possessive-only (NEW)
        if p.startswith("^\\s*([A-Za-z]"):
            subj_raw = m.group(1); rel_raw = m.group(2)
            return (_canon_subject(subj_raw.strip("'\" ")), _normalize_synonym(rel_raw))

        # 3) where was/is <subject> born/from
        if p.startswith("^\\s*where\\s+"):
            subj_raw = m.group(1); rel_raw = "birthplace"
            return (_canon_subject(subj_raw.strip("'\" ")), _normalize_synonym(rel_raw))

        # 4) did/does/has … have pets/kids/siblings/husband
        if p.startswith("^\\s*(?:did|does|has|have)"):
            subj_raw = m.group(1); rel_raw = m.group(2)
            return (_canon_subject(subj_raw.strip("'\" ")), _normalize_synonym(rel_raw))

        # default: two-capture patterns like "pam siblings", "who is pam's husband"
        subj_raw = m.group(1); rel_raw = m.group(2)
        return (_canon_subject(subj_raw.strip("'\" ")), _normalize_synonym(rel_raw))

    # natural alias fallback
    alias = _natural_alias(text)
    if alias:
        return alias

    return None

# =============================================================================
# Memory Access + Answer Formatting
# =============================================================================

def call_memory_lookup(subj: str, rel: str) -> Optional[Any]:
    for name in ["ask", "get", "get_fact", "recall", "query", "answer", "search", "find"]:
        if hasattr(memory, name) and callable(getattr(memory, name)):
            try:
                return getattr(memory, name)(subj, rel)
            except Exception:
                continue
    return None

REL_VARIANTS = {
    "siblings": ["siblings", "brothers and sisters", "sibling"],
    "children": ["children", "kids", "child"],
    "birthplace": ["birthplace", "birth place", "place of birth", "born", "from"],
    "raised by": ["raised by", "raised", "primary caregiver"],
    "favorite restaurants": ["favorite restaurants", "restaurants"],
    "favorite foods": ["favorite foods", "favorite meals", "meals", "foods"],
    "schools attended": ["schools attended", "education", "educated at", "schools"],
    "pet": ["pet", "pets", "animals", "pet(s)"],
    "husband": ["husband", "spouse"],
    "full name": ["full name", "name"],
    "birthday": ["birthday", "dob", "date of birth", "birth date", "birthdate"],
}

def lookup_with_variants(subj: str, rel: str):
    """
    Try (subject × relation) across spelling/case variants so we hit your stored keys.
    """
    subjects = _subject_candidates(subj)
    variants = REL_VARIANTS.get(rel, [rel])
    tried = set()
    for s in subjects:
        for r in variants:
            for S in (s, s.lower()):
                for R in (r, r.lower()):
                    key = (S, R)
                    if key in tried:
                        continue
                    tried.add(key)
                    ans = call_memory_lookup(S, R)
                    if ans not in (None, "", [], {}):
                        return ans
    return None

def _join_list(items) -> str:
    items = [str(x).strip() for x in items if str(x).strip()]
    if not items: return ""
    if len(items) == 1: return items[0]
    return ", ".join(items[:-1]) + ", and " + items[-1]

# ---- PETS CONSOLIDATION (unchanged) -----------------------------------------
PET_HINT_KEYS = [
    "pet",
    "did you ever have a pet as a kid",
    "did pamela butler have any other family dogs",
    "what breed was the family dog yasha",
    "what happened to yasha",
]
PET_NAME_RE = re.compile(r"\b(Bell|Bail|Yasha|Pierre)\b", re.I)
PET_BREED_RE = re.compile(r"\b(German Shepherd|Siberian/Alaskan Husky|Husky|Poodle)\b", re.I)

def pet_answer(subj: str):
    candidates = []
    for s in _subject_candidates(subj):
        for k in PET_HINT_KEYS:
            a = call_memory_lookup(s, k)
            if not a:
                continue
            texts = a if isinstance(a, (list, tuple)) else [a]
            for t in texts:
                T = str(t)
                names = set(n.capitalize() for n in PET_NAME_RE.findall(T))
                # normalize Bail→Bell
                if "Bail" in names and "Bell" not in names:
                    names.discard("Bail"); names.add("Bell")
                for n in names:
                    label = n
                    if n.lower() == "yasha":
                        label = f"{n} (Husky)"
                    elif n.lower() == "bell":
                        label = f"{n} (German Shepherd)"
                    candidates.append(label)

    if not candidates:
        a = lookup_with_variants(subj, "pet")
        if isinstance(a, (list, tuple)):
            candidates = [str(x) for x in a]
        elif a:
            candidates = [str(a)]

    seen, result = set(), []
    for c in candidates:
        key = c.lower().strip()
        if key and key not in seen:
            seen.add(key)
            result.append(c)
    return result or None

def naturalize(subject: str, relation: str, obj: Any) -> str:
    rel = relation.lower().strip(); s = subject.strip()
    if isinstance(obj, (list, tuple)) and not isinstance(obj, str):
        j = _join_list(obj)
        if rel == "children": return f"{s}'s children are {j}."
        if rel == "siblings": return f"{s}'s siblings are {j}."
        if rel == "favorite restaurants": return f"{s}'s favorite restaurants are {j}."
        if rel == "favorite foods": return f"{s}'s favorite foods are {j}."
        if rel == "schools attended": return f"{s} attended {j}."
        if rel == "raised by": return f"{s} was raised by {j}."
        if rel == "pet": return f"{s}'s pets are {j}."
        return f"{s}'s {rel} are {j}."
    o = str(obj).strip()
    mapping = {
        "husband": f"{o} is {s}'s husband.",
        "wife": f"{o} is {s}'s wife.",
        "father": f"{o} is the father of {s}.",
        "mother": f"{o} is the mother of {s}.",
        "son": f"{o} is {s}'s son.",
        "daughter": f"{o} is {s}'s daughter.",
        "brother": f"{o} is {s}'s brother.",
        "sister": f"{o} is {s}'s sister.",
        "mission": f"{s}'s mission is: {o}",
        "purpose": f"{s}'s purpose is: {o}",
        "goal": f"{s}'s goal is: {o}",
        "full name": f"{s}'s full name is {o}.",
        "birthday": f"{s}'s birthday is {o}.",
        "birthplace": f"{s} was born in {o}.",
    }
    return mapping.get(rel, f"{o} is the {relation} of {s}.")

def coerce_answer_to_text(ans: Any, subj: Optional[str], rel: Optional[str]) -> Optional[str]:
    if ans is None:
        return None
    if isinstance(ans, (list, tuple)) and not isinstance(ans, str):
        return naturalize(subj or "", rel or "", list(ans))
    if isinstance(ans, str):
        txt = ans.strip()
        if not txt:
            return None
        if subj and rel and (len(txt.split()) <= 6) and not txt.endswith(('.', '!', '?')):
            return naturalize(subj, rel, txt)
        return txt
    if isinstance(ans, dict):
        s = ans.get("subject", subj)
        r = ans.get("relation", rel)
        o = ans.get("object") or ans.get("value")
        if s and r and o is not None:
            return naturalize(str(s), str(r), o)
    if isinstance(ans, (tuple, list)) and len(ans) >= 3:
        s, r, o = ans[0], ans[1], ans[2]
        return naturalize(str(s), str(r), o)
    try:
        return json.dumps(ans, ensure_ascii=False)
    except Exception:
        return str(ans)

# ---- Rewriter (gentle; skipped for lists/group) ------------------------------
def rewrite_fluent(raw_text: str) -> str:
    if not OPENAI_API_KEY:
        return raw_text
    try:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "temperature": 0.2,
            "max_tokens": 60,
            "messages": [
                {"role": "system",
                 "content": "Rewrite the user's sentence as ONE warm, natural sentence. Do not add opinions or extra facts. Keep under 25 words."},
                {"role": "user", "content": raw_text}
            ]
        }
        r = requests.post(url, headers=headers, json=payload, timeout=12)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"Rewriter error: {e}")
        return raw_text

@lru_cache(maxsize=256)
def _rewrite_cached(s: str) -> str:
    return rewrite_fluent(s)

# =============================================================================
# Routes
# =============================================================================

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/save", methods=["POST"])
def save():
    data = request.get_json(force=True) or {}
    subject = (data.get("subject") or "")
    relation = (data.get("relation") or "")
    obj = data.get("object")

    if not (validate_input_str(subject) and validate_input_str(relation)):
        return jsonify({"success": False, "message": "Invalid subject or relation."}), 400

    relation = _normalize_synonym(relation)
    if isinstance(obj, str):
        obj = _clean_text(obj)
        if relation in {"children", "siblings", "favorite foods", "favorite restaurants", "schools attended", "raised by", "pet"}:
            obj = _split_names_loose(obj)

    logger.info(f"/save :: subject={subject} relation={relation} obj={obj}")

    try:
        if hasattr(memory, "save_fact"):
            res = memory.save_fact(subject.strip(), relation.strip(), obj)
            ok, msg = (bool(res[0]), str(res[1])) if isinstance(res, tuple) else (True, "Fact saved.")
        else:
            return jsonify({"success": False, "message": "save_fact not available."}), 500
        return jsonify({"success": ok, "message": msg})
    except Exception as e:
        logger.error(f"Save error: {e}")
        return jsonify({"success": False, "message": f"Save error: {e}"}), 500

@app.route("/clear", methods=["POST"])
def clear():
    try:
        if hasattr(memory, "clear"):
            memory.clear()
            return jsonify({"success": True, "message": "Memory cleared."})
        return jsonify({"success": False, "message": "Memory.clear() not available."}), 500
    except Exception as e:
        logger.error(f"Clear error: {e}")
        return jsonify({"success": False, "message": f"Clear error: {e}"}), 500

@app.route("/mem/export", methods=["GET"])
def mem_export():
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify({"ok": False, "error": "Unauthorized"}), 403
    try:
        if hasattr(memory, "export_all"):
            return jsonify({"ok": True, "data": memory.export_all()})
        return jsonify({"ok": False, "error": "export_all not available"}), 500
    except Exception as e:
        logger.error(f"/mem/export error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/ask/general", methods=["POST"])
def ask_general():
    """
    1) Try to parse a natural-language fact and SAVE it.
    2) Otherwise, parse as a question and LOOKUP (with variants + pet consolidation).
    3) Otherwise, friendly fallback.
    """
    data = request.get_json(force=True) or {}
    raw = (data.get("text") or data.get("query") or "")
    if not validate_input_str(raw, MAX_INPUT_LEN):
        return jsonify({"ok": False, "source": "error", "response": "Please ask a shorter question."}), 400

    text = _loose_possessives(_clean_text(raw))
    logger.info(f"/ask/general :: {text[:160]}")

    # NATURAL-LANGUAGE SAVE (e.g., "Pams husband is Rickey")
    triplet = parse_assertion(text)
    if triplet:
        subj, rel, obj = triplet
        try:
            ok, msg = memory.save_fact(subj, rel, obj)
        except Exception as e:
            logger.error(f"Save via assertion error: {e}")
            return jsonify({"ok": False, "source": "memory/save", "response": f"Save error: {e}"})
        if ok:
            saved_line = (
                f"Got it — I’ll remember that {subj}'s {rel} is "
                f"{_join_list(obj) if isinstance(obj, list) else obj}."
            )
            return jsonify({"ok": True, "source": "memory/save", "response": saved_line})
        else:
            return jsonify({"ok": False, "source": "memory/save", "response": msg})

    # QUESTION LOOKUP
    sr = parse_subject_relation(text)
    if sr:
        subj, rel = sr

        # Pets: smart consolidation across multiple keys
        ans = None
        if rel == "pet":
            ans = pet_answer(subj)
        if ans is None:
            ans = lookup_with_variants(subj, rel)

        ans_text = coerce_answer_to_text(ans, subj, rel)
        if ans_text:
            is_group_rel = rel in {"children", "siblings", "favorite restaurants", "favorite foods", "schools attended", "raised by", "pet"}
            is_list_ans = isinstance(ans, (list, tuple)) and not isinstance(ans, str)
            fluent = ans_text if (is_group_rel or is_list_ans) else _rewrite_cached(ans_text)
            return jsonify({"ok": True, "source": "memory/lookup", "response": fluent})

    # fallback
    return jsonify({
        "ok": False,
        "source": "fallback",
        "response": "I don’t have that yet. Try: “Pam birthday”, “Pam siblings”, or save a fact like “Pam’s mother is Esther.”"
    })

# =============================================================================
# Dev server
# =============================================================================

from flask import request, jsonify
from knowledgefeed import load_folder
from soulnode_memory import SoulNodeMemory

# Global memory instance
MEM = SoulNodeMemory("Ty")

@app.post("/knowledge/reindex")
def knowledge_reindex():
    """Re-ingest all .md/.txt files in knowledge/ into memory."""
    count = load_folder("knowledge", MEM)
    return jsonify({"ok": True, "ingested": count})

@app.get("/knowledge/test")
def knowledge_test():
    """Quick sanity check recall."""
    return jsonify({
        "pam_child": MEM.ask("Pam", "child"),
        "ty_parent": MEM.ask("Ty", "parent")
    })

@app.get("/knowledge/query")
def knowledge_query():
    """Ask memory with subject + relation via query string."""
    subject = request.args.get("subject")
    relation = request.args.get("relation")
    if not subject or not relation:
        return jsonify({"ok": False, "error": "Please provide subject and relation"}), 400

    answer = MEM.ask(subject, relation)
    return jsonify({
        "ok": True,
        "subject": subject,
        "relation": relation,
        "answer": answer
    })

import os
from datetime import datetime

@app.get("/assistant/checkin")
def assistant_checkin():
    """
    Minimal morning brief built from memory + knowledge folder.
    Safe if something's missing.
    """
    # facts we care about (use what we have; None if absent)
    pam_child = MEM.ask("Pam", "child")
    ty_parent = MEM.ask("Ty", "parent")

    # how many facts in memory
    fact_count = len(MEM.facts)

    # how many .md/.txt files in knowledge/
    note_files = 0
    note_lines = 0
    try:
        for root, _, files in os.walk("knowledge"):
            for fn in files:
                if fn.lower().endswith((".md", ".txt")):
                    note_files += 1
                    try:
                        with open(os.path.join(root, fn), "r", encoding="utf-8") as f:
                            note_lines += sum(1 for _ in f)
                    except Exception:
                        pass
    except Exception:
        pass

    brief = [
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"Knowledge: {note_files} note file(s), {note_lines} line(s) scanned",
        f"Memory size: {fact_count} fact(s)",
        f"Family check: Pam’s child -> {pam_child or 'unknown'} / Ty’s parent -> {ty_parent or 'unknown'}",
        "Next actions:",
        "- Add one new fact line to knowledge/family_facts.md",
        "- Hit /knowledge/reindex to ingest",
        "- Ask /knowledge/query?subject=...&relation=...",
    ]

    return jsonify({"ok": True, "brief": brief})

@app.post("/knowledge/add")
def knowledge_add():
    """
    Add one fact directly into memory.
    Body JSON: {"subject": "...", "relation": "...", "object": "..."}
    """
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"ok": False, "error": "Invalid JSON"}), 400

    subject = (data.get("subject") or "").strip()
    relation = (data.get("relation") or "").strip()
    obj = data.get("object")

    ok, msg = MEM.save_fact(subject, relation, obj)
    status = 200 if ok else 400
    return jsonify({"ok": ok, "message": msg, "subject": subject, "relation": relation, "object": obj}), status

# --- Natural-language ask -----------------------------------------------------
import re

# Name pattern (letters, spaces, dashes, apostrophes, periods)
_NAME = r"[A-Za-z][A-Za-z\-\.' ]+"

# Relations: normalize synonyms; some map to multiple candidates (e.g., spouse)
_REL_MAP = {
    "mom": "mother",
    "mother": "mother",
    "dad": "father",
    "father": "father",
    "kid": "child",
    "child": "child",
    "children": "child",
    "son": "child",
    "daughter": "child",
    "parent": "parent",
    "parents": "parent",
    "husband": "husband",
    "wife": "wife",
    "spouse": ["husband", "wife"],
}

_PATTERNS = [
    # "who/what is/was X's Y?"
    re.compile(
        rf"^(?:who|what)\s+(?:is|was|are|'s)\s+(?P<subj>{_NAME})\s*(?:'s|s')\s+(?P<rel>[A-Za-z]+)\s*\?$",
        re.IGNORECASE,
    ),
    # "who/what is/was the Y of X?"
    re.compile(
        rf"^(?:who|what)\s+(?:is|was|are)\s+the\s+(?P<rel>[A-Za-z]+)\s+of\s+(?P<subj>{_NAME})\s*\?$",
        re.IGNORECASE,
    ),
]

def _norm_name(s: str) -> str:
    return (s or "").strip()

def _relation_candidates(rel: str):
    base = (rel or "").strip().lower()
    mapped = _REL_MAP.get(base, base)
    return mapped if isinstance(mapped, list) else [mapped]

def _parse_question(q: str):
    if not q:
        return None
    text = q.strip()
    # ensure it ends with a question mark for our patterns
    if not text.endswith("?"):
        text = text + "?"
    for rx in _PATTERNS:
        m = rx.match(text)
        if m:
            subj = _norm_name(m.group("subj"))
            rel = (m.group("rel") or "").strip().lower()
            return subj, rel
    return None # not understood

@app.get("/ask")
def ask_nl():
    """
    Natural-language ask:
      /ask?q=Who%20is%20Kobe's%20parent?
      /ask?q=Who%20is%20the%20child%20of%20Pam?
      /ask?q=Who%20is%20Ty's%20mom?
    """
    q = request.args.get("q") or request.args.get("question")
    parsed = _parse_question(q)
    if not parsed:
        return jsonify({"ok": False, "error": "Could not parse question.", "q": q}), 400

    subj, rel_raw = parsed
    candidates = _relation_candidates(rel_raw)

    answers = []
    for rel in candidates:
        ans = MEM.ask(subj, rel)
        if ans is not None:
            answers.append(ans)

    # Deduplicate while preserving order (in case spouse returns both)
    seen = set()
    answers = [a for a in answers if not (a in seen or seen.add(a))]

    return jsonify({
        "ok": True,
        "q": q,
        "subject": subj,
        "parsed_relation": rel_raw,
        "tried_relations": candidates,
        "answer": (answers[0] if answers else None),
        "answers": answers, # list form, may be empty
    })

@app.get("/ask/demo")
def ask_demo():
    """Run a small suite of natural-language questions in one shot."""
    qs = [
        "Who is Kobe's parent?",
        "Who is the child of Pam?",
        "Who is Ty's mom?",
        "Who is Pam's spouse?",
    ]
    results = []
    for q in qs:
        r = app.test_client().get("/ask", query_string={"q": q})
        try:
            results.append({"q": q, "resp": r.get_json()})
        except Exception:
            results.append({"q": q, "resp": {"ok": False, "error": "Invalid response"}})
    return jsonify({"ok": True, "count": len(results), "results": results})

    from datetime import datetime

@app.get("/knowledge/stats")
def knowledge_stats():
    """
    Snapshot of memory/knowledge health.
    """
    # Pull from MEM.records (rich view with timestamps)
    recs = list(MEM.records.values())

    total_facts = len(recs)
    subjects = sorted({ (r.get("subject") or "").strip() for r in recs if r.get("subject") })
    relations = sorted({ (r.get("relation") or "").strip().lower() for r in recs if r.get("relation") })

    # last updated time (ISO string) if any
    def _to_dt(s):
        try:
            # strip trailing Z if present
            s = (s or "").rstrip("Z")
            return datetime.fromisoformat(s)
        except Exception:
            return None

    last_updated = None
    for r in recs:
        dt = _to_dt(r.get("updated_at"))
        if dt and (last_updated is None or dt > last_updated):
            last_updated = dt

    # small histogram of relations (top 5)
    rel_counts = {}
    for r in recs:
        rel = (r.get("relation") or "").strip().lower()
        if not rel:
            continue
        rel_counts[rel] = rel_counts.get(rel, 0) + 1
    top_relations = sorted(rel_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    return jsonify({
        "ok": True,
        "totals": {
            "facts": total_facts,
            "unique_subjects": len(subjects),
            "unique_relations": len(relations),
        },
        "top_relations": [{"relation": k, "count": v} for k, v in top_relations],
        "last_updated": (last_updated.isoformat() + "Z") if last_updated else None,
    })

    # --- Knowledge watch: only reindex when note files change --------------------
import threading, time, os
from typing import Dict, Tuple

_WATCH_ON = False
_WATCH_THREAD = None
_WATCH_SNAPSHOT: Dict[str, float] = {} # path -> mtime
_WATCH_INTERVAL_SEC = 60 # check every 60s
_WATCH_FOLDER = "knowledge"

def _snapshot_folder(root: str) -> Dict[str, float]:
    snap = {}
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith((".md", ".txt")):
                continue
            fp = os.path.join(dirpath, fn)
            try:
                snap[fp] = os.path.getmtime(fp)
            except Exception:
                pass
    return snap

def _has_changes(prev: Dict[str, float], curr: Dict[str, float]) -> bool:
    if prev.keys() != curr.keys():
        return True
    for k, v in curr.items():
        if prev.get(k) != v:
            return True
    return False

def _watch_loop():
    global _WATCH_ON, _WATCH_SNAPSHOT
    # initial snapshot
    try:
        _WATCH_SNAPSHOT = _snapshot_folder(_WATCH_FOLDER)
    except Exception:
        _WATCH_SNAPSHOT = {}
    while _WATCH_ON:
        try:
            time.sleep(_WATCH_INTERVAL_SEC)
            curr = _snapshot_folder(_WATCH_FOLDER)
            if _has_changes(_WATCH_SNAPSHOT, curr):
                # Only reindex when files were added/removed/modified
                count = load_folder(_WATCH_FOLDER, MEM)
                _WATCH_SNAPSHOT = curr
                print(f"[watch] changes detected → ingested: {count}")
        except Exception as e:
            # keep the loop alive; log and continue
            print(f"[watch] error: {e}")

@app.post("/knowledge/watch/start")
def knowledge_watch_start():
    """Begin watching the knowledge folder for changes."""
    global _WATCH_ON, _WATCH_THREAD
    if _WATCH_ON:
        return jsonify({"ok": True, "message": "already running"})
    _WATCH_ON = True
    _WATCH_THREAD = threading.Thread(target=_watch_loop, daemon=True)
    _WATCH_THREAD.start()
    return jsonify({"ok": True, "message": "watch started", "interval_seconds": _WATCH_INTERVAL_SEC})

@app.post("/knowledge/watch/stop")
def knowledge_watch_stop():
    """Stop watching the knowledge folder."""
    global _WATCH_ON
    _WATCH_ON = False
    return jsonify({"ok": True, "message": "watch stopped"})

@app.get("/knowledge/watch/status")
def knowledge_watch_status():
    """Report whether watch is running and last snapshot info."""
    return jsonify({
        "ok": True,
        "running": _WATCH_ON,
        "files_tracked": len(_WATCH_SNAPSHOT),
        "interval_seconds": _WATCH_INTERVAL_SEC
    })

@app.post("/knowledge/watch/ping")
def knowledge_watch_ping():
    """Force an immediate rescan of the knowledge folder without waiting for the interval."""
    global _WATCH_SNAPSHOT
    try:
        curr = _snapshot_folder(_WATCH_FOLDER)
        if _has_changes(_WATCH_SNAPSHOT, curr):
            count = load_folder(_WATCH_FOLDER, MEM)
            _WATCH_SNAPSHOT = curr
            return jsonify({"ok": True, "message": f"changes detected → ingested {count}", "files": len(curr)})
        else:
            return jsonify({"ok": True, "message": "no changes detected", "files": len(curr)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})

        # --- TALK: SoNo's fluent text replies (memory + GPT + general knowledge) -----
import os, re
from flask import request, jsonify
from openai import OpenAI

TALK_MODE = os.getenv("SONO_TALK_MODE", "gpt") # "gpt" or "stub"
OPENAI_MODEL = os.getenv("SONO_MODEL", "gpt-4o-mini")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Ensure identity seeds exist (safe no-op if already present)
def _ensure_identity_seeds():
    seeds = [
        ("SoNo", "identity", "I am SoulNode (SoNo), Ty Butler’s AI co-pilot."),
        ("Ty", "identity", "You are Ty Butler: founder of New Chapter Media Group, father of TJ, Kobe, and Ivy."),
    ]
    for s, r, o in seeds:
        try:
            MEM.save_fact(s, r, o)
        except Exception:
            pass
_ensure_identity_seeds()

# --- relation synonyms (for query understanding) -----------------------------
_REL_SYNONYMS = {
    "mom":"mother","mother":"mother","dad":"father","father":"father",
    "kids":"child","children":"child","son":"child","daughter":"child",
    "spouse":"spouse","husband":"husband","wife":"wife",
    "parent":"parent","parents":"parent",
    "born":"birthplace","birthplace":"birthplace",
    "support":"support","hospital":"hospital","covid":"covid",
}

# --- name aliasing so questions still match facts ----------------------------
_ALIASES = {
    "rickey": "rickey", "ricky": "rickey",
    "pam": "pam", "pamela": "pam",
    "ty": "ty", "tyease": "ty",
    "tj": "tj", "t.j.": "tj",
    "kobe": "kobe", "ivy": "ivy",
    "sono": "sono", "soulnode": "sono"
}

_NAME_RX = r"[A-Za-z][A-Za-z\-\.' ]+"
_WORD_RX = r"[A-Za-z]{3,}"
_norm = lambda s: (s or "").strip().lower()

def _alias(name: str) -> str:
    n = _norm(name)
    return _ALIASES.get(n, n)

def _extract_terms(text: str):
    # names via regex, then normalize with aliases
    names = { _alias(m.strip()) for m in re.findall(_NAME_RX, text or "", flags=re.IGNORECASE) }
    # general words
    words = { w.lower() for w in re.findall(_WORD_RX, text or "", flags=re.IGNORECASE) }
    # relation set (normalize via synonyms)
    rels = set()
    for w in list(words):
        base = _REL_SYNONYMS.get(w, w)
        if base in _REL_SYNONYMS.values():
            rels.add(base)
    # anchors
    names.update({"sono","ty"})
    return names, words, rels

def _score_record(q_names, q_words, q_rels, rec):
    s = _alias(rec.get("subject") or "")
    r = _norm(rec.get("relation") or "")
    o_val = rec.get("object")
    o = _alias(o_val) if isinstance(o_val, str) else ""

    score = 0.0
    # direct hits matter most
    if s in q_names: score += 6.0
    if o and o in q_names: score += 5.0
    if r in q_rels: score += 6.0

    # light keyword bump (keep tiny so long narratives don't drown crisp facts)
    for w in q_words:
        if not w: 
            continue
        if w in r or w in s or (o and w in o):
            score += 0.5

    return score

def _ranked_facts(question: str, limit: int = 25):
    q_names, q_words, q_rels = _extract_terms(question)

    # If the question clearly asks about a specific relationship, prefer those facts first
    REL_GROUPS = {
        "spouse": {"spouse", "husband", "wife"},
        "parent": {"parent", "mother", "father"},
        "child": {"child", "son", "daughter"},
        "birthplace": {"birthplace"},
    }
    target_rel_set = None
    for group in REL_GROUPS.values():
        if any(r in group for r in q_rels):
            target_rel_set = group
            break

    scored = []
    for rec in MEM.records.values():
        sc = _score_record(q_names, q_words, q_rels, rec)
        if sc < 1.0:
            continue
        scored.append((sc, rec))

    # If we detected a relation in the question, keep those matches first
    if target_rel_set:
        primary = [(sc, rec) for sc, rec in scored
                   if _norm(rec.get("relation") or "") in target_rel_set]
        secondary = [(sc, rec) for sc, rec in scored
                     if _norm(rec.get("relation") or "") not in target_rel_set]

        primary.sort(key=lambda x: x[0], reverse=True)
        secondary.sort(key=lambda x: x[0], reverse=True)
        merged = primary + secondary
        top = [rec for sc, rec in merged[:limit]]
    else:
        scored.sort(key=lambda x: x[0], reverse=True)
        top = [rec for sc, rec in scored[:limit]]

    if not top:
        # backstop: include a few identity facts if nothing matched
        for rec in MEM.records.values():
            subj = _alias(rec.get("subject") or "")
            if subj in {"sono", "ty"}:
                top.append(rec)
            if len(top) >= 10:
                break
    return top
def _mem_context_lines(recs, cap=25):
    lines = []
    for rec in recs[:cap]:
        lines.append(f"- {rec.get('subject')} | {rec.get('relation')} | {rec.get('object')}")
    return "\n".join(lines) if lines else "(no relevant facts)"

@app.post("/talk")
def talk():
    data = request.get_json(force=True) or {}
    q = (data.get("q") or "").strip()
    debug = bool(data.get("debug"))
    if not q:
        return jsonify({"ok": False, "error": "Missing q"}), 400

    facts = _ranked_facts(q, limit=25)
    mem_context = _mem_context_lines(facts, cap=25)

    # Stub mode or missing key -> safe fallback that never breaks your app
    if TALK_MODE != "gpt" or not os.getenv("OPENAI_API_KEY"):
        reply = (
            "I hear you. Here’s what’s relevant from memory:\n"
            f"{mem_context}\n\n"
            "One next step: choose the smallest action that reduces friction today."
        )
        return jsonify({
            "ok": True,
            "mode": "stub",
            "reply": reply,
            **({"facts_used": len(facts), "memory_slice": mem_context} if debug else {})
        })

    # GPT mode: blend memory + general knowledge
    system_prompt = (
        "You are SoulNode (SoNo), Ty Butler’s AI co-pilot.\n"
        "Voice: plain, supportive, strategic. No fluff.\n"
        "Use TWO sources:\n"
        "1) PERSONAL MEMORY (bullets provided) — ground truth for Ty’s life.\n"
        "2) YOUR GENERAL KNOWLEDGE — for public facts (Bible, NBA, etc.).\n"
        "Rules: Prefer memory if there’s any conflict; if unknown, say so briefly and offer one next step.\n"
        "Keep replies under ~6 sentences unless Ty asks for more."
    )
    user_prompt = (
        f"User said:\n{q}\n\n"
        f"Personal memory facts (may be empty):\n{mem_context}\n\n"
        "Reply in SoNo’s voice, weaving in relevant memory when applicable. "
        "If the question is general (e.g., Bible/NBA/etc.), answer from your own knowledge. "
        "Be concise and actionable."
    )

    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_prompt},
            ],
            temperature=0.7,
            max_tokens=350,
        )
        reply = resp.choices[0].message.content
        return jsonify({
            "ok": True,
            "mode":"gpt",
            "model": OPENAI_MODEL,
            "reply": reply,
            **({"facts_used": len(facts), "memory_slice": mem_context} if debug else {})
        })
    except Exception as e:
        # graceful fallback
        reply = (
            "I’m here. Fluent engine had an issue, so using memory snapshot instead:\n"
            f"{mem_context}\n\n"
            "Next step: try again or keep it simple."
        )
        return jsonify({
            "ok": True,
            "mode":"stub-fallback",
            "error": str(e),
            "reply": reply,
            **({"facts_used": len(facts), "memory_slice": mem_context} if debug else {})
        })

 
    
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
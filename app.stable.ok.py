# app.py — SoNo (single-file: identity + teach + memory + pam.txt + GPT fallback)
# --------------------------------------------------------------------------------
# This file stands alone:
# - Loads pam.txt + *_profile.json into MemoryStore on boot
# - Rich TEACH parser (“remember…”, “set… to…”, “… — remember that”)
# - Expanded QA patterns (who/what/where variants) + alias normalization
# - Memory-first routing, then pam.txt retrieval, then GPT fallback
# - Simple Flask routes: /, /ask, /healthz, /mem/export

import os, re, json
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from functools import lru_cache

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template

# --- Local modules you already have ---
# Make sure these files exist exactly with these names in your repo.
from memory_store import MemoryStore
from intent import parse_intent
from ingest_pam import load_pam_facts # expects load_pam_facts(Path("data/pam.txt")) -> Dict[str,str]
from retriever_pam import retrieve_pam_answer # optional retriever; we try it after memory misses

# --- OpenAI client (new SDK) ---
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ====================== App init ======================
app = Flask(__name__)
store = MemoryStore()

def _trace(*items):
    try:
        print("TRACE:", *items, flush=True)
    except Exception:
        pass

# ====================== Identity ======================
IDENTITY = {
    "name": "SoNo",
    "creators": "Ty Butler and New Chapter Media Group",
    "mission": "to be a calm, helpful companion for Pam—listening, remembering, and giving clear answers."
}

def identity_answer(text: str) -> Optional[str]:
    t = (text or "").lower()
    if any(p in t for p in ["who are you", "what are you", "tell me about yourself"]):
        return f"I'm {IDENTITY['name']}, created by {IDENTITY['creators']}. My mission is {IDENTITY['mission']}"
    if any(p in t for p in ["your name", "what is your name", "what's your name"]):
        return f"My name is {IDENTITY['name']}."
    if any(p in t for p in ["who created you", "who made you"]):
        return f"I was created by {IDENTITY['creators']}."
    if any(p in t for p in ["your mission", "what is your mission", "what's your mission"]):
        return f"My mission is {IDENTITY['mission']}."
    return None

# ====================== Preload: pam.txt ======================
PAM_FACTS: Dict[str, str] = {}
try:
    pam_dict = load_pam_facts(Path("data/pam.txt")) # your helper parses pam.txt to a dict
    for rel, val in (pam_dict or {}).items():
        r = (rel or "").strip().lower()
        v = str(val).strip()
        if not v:
            continue
        PAM_FACTS[r] = v
        if r == "mom":
            # store Ty→mom for “Who is Ty’s mom?”
            store.remember("ty", "mom", v)
        else:
            # all other facts → Pam
            store.remember("pam", r, v)
    _trace(f"pam.txt loaded: {len(PAM_FACTS)} facts")
except Exception as e:
    _trace(f"pam.txt preload skipped: {e.__class__.__name__}: {e}")

# ====================== Preload: profiles ======================
def _seed_profile_into_memory(path: Path):
    try:
        if not path.is_file():
            _trace(f"Profile not found: {path}")
            return
        with path.open("r", encoding="utf-8") as f:
            prof = json.load(f)
        sub = str(prof.get("subject", "")).strip().lower()
        facts = prof.get("facts") or {}
        if not (sub and isinstance(facts, dict) and facts):
            _trace(f"Profile missing subject/facts: {path.name}")
            return
        for rel, obj in facts.items():
            rel_n = str(rel).strip().lower()
            val = str(obj).strip()
            if rel_n and val:
                store.remember(sub, rel_n, val)
        _trace(f"Profile loaded: {path.name} ({len(facts)} facts)")
    except Exception as e:
        _trace(f"Profile load failed for {path.name}: {e.__class__.__name__}: {e}")

try:
    data_dir = Path("data")
    for p in data_dir.glob("*_profile.json"):
        _seed_profile_into_memory(p)
except Exception as e:
    _trace(f"Profiles preload error: {e.__class__.__name__}: {e}")

# ====================== Aliases & Normalization ======================
_REL_ALIASES: Dict[str, str] = {
    "name": "full name",
    "full_name": "full name",
    "birth place": "birthplace",
    "where born": "birthplace",
    "born": "birthplace",
    "home": "hometown",
    "from": "hometown",
    "grew up": "hometown",
    "raised": "hometown",
    "mother": "mom",
    "guardian": "raised_by",
    "school": "schools",
    "schools attended": "schools",
    "pets owned": "pets",
    "fav color": "favorite color",
    "favorite colour": "favorite color",
    "colour": "color",
}

def normalize_relation(rel: Optional[str]) -> Optional[str]:
    if not rel:
        return None
    r = rel.strip().lower()
    return _REL_ALIASES.get(r, r)

# ====================== TEACH (natural phrases) ======================
_TEACH_PATTERNS = [
    re.compile(r"""^\s*(remember|save|store|lock\s*in)\s+
                    (?P<sub>[a-z][\w\s']*)'s\s+(?P<rel>[\w\s]+?)\s+(is|=)\s+(?P<val>.+?)\s*$""", re.I | re.X),
    re.compile(r"""^\s*(set|update)\s+
                    (?P<sub>[a-z][\w\s']*)'s\s+(?P<rel>[\w\s]+?)\s+to\s+(?P<val>.+?)\s*$""", re.I | re.X),
    re.compile(r"""^\s*(note\s+that|please\s+remember\s+that)\s+
                    (?P<sub>[a-z][\w\s']*)'s\s+(?P<rel>[\w\s]+?)\s+(is|=)\s+(?P<val>.+?)\s*$""", re.I | re.X),
    re.compile(r"""^\s*(?P<sub>[a-z][\w\s']*)'s\s+(?P<rel>[\w\s]+?)\s+(is|=)\s+(?P<val>.+?)\s*[—-]\s*remember\s+that\s*$""", re.I),
    re.compile(r"""^\s*(teach|learn)\s*:\s*
                    (?P<sub>[a-z][\w\s']*)\s+(?P<rel>[\w\s]+?)\s*[-–>]\s*(?P<val>.+?)\s*$""", re.I | re.X),
]

def parse_teach(text: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    t = (text or "").strip()
    if not t:
        return (None, None, None)
    for rx in _TEACH_PATTERNS:
        m = rx.match(t)
        if m:
            sub = (m.group("sub") or "").strip().lower()
            rel = normalize_relation(m.group("rel"))
            val = (m.group("val") or "").strip().strip(".")
            return (sub, rel, val) if (sub and rel and val) else (None, None, None)
    return (None, None, None)

# ====================== QA patterns (fast lane) ======================
_QA_PATTERNS = [
    # Ty’s mom
    (re.compile(r"\bwho\s+is\s+ty'?s\s+(mom|mother)\b", re.I), ("ty", "mom")),
    (re.compile(r"\bwhat('?s| is)\s+ty'?s\s+mom'?s?\s+name\b", re.I), ("ty", "mom")),
    # Pam full name
    (re.compile(r"\bwhat('?s| is)\s+pam'?s\s+full\s+name\b", re.I), ("pam", "full name")),
    (re.compile(r"\bwhat\s+is\s+the\s+full\s+name\s+of\s+pam\b", re.I), ("pam", "full name")),
    (re.compile(r"\bpam'?s\s+full\s+name\b", re.I), ("pam", "full name")),
    # Birthplace
    (re.compile(r"\bwhere\s+was\s+pam\s+born\b", re.I), ("pam", "birthplace")),
    (re.compile(r"\bwhen\s+and\s+where\s+was\s+pam\s+born\b", re.I), ("pam", "birthplace")),
    (re.compile(r"\bpam'?s\s+birthplace\b", re.I), ("pam", "birthplace")),
    (re.compile(r"\bwhere\s+was\s+she\s+born\b", re.I), ("pam", "birthplace")),
    # Hometown / raised
    (re.compile(r"\bwhere\s+(did|was)\s+pam\s+(grow\s*up|raised)\b", re.I), ("pam", "hometown")),
    (re.compile(r"\bwhere\s+is\s+pam\s+from\b", re.I), ("pam", "hometown")),
    (re.compile(r"\bwhat'?s\s+pam'?s\s+hometown\b", re.I), ("pam", "hometown")),
    (re.compile(r"\bwhere\s+did\s+she\s+grow\s+up\b", re.I), ("pam", "hometown")),
    # Schools
    (re.compile(r"\bwhich\s+schools?\s+did\s+pam\s+attend\b", re.I), ("pam", "schools")),
    (re.compile(r"\bwhere\s+did\s+pam\s+go\s+to\s+school\b", re.I), ("pam", "schools")),
    (re.compile(r"\bpam'?s\s+schools?\b", re.I), ("pam", "schools")),
    # Pets
    (re.compile(r"\b(did|does)\s+pam\s+have\s+pets?\b", re.I), ("pam", "pets")),
    (re.compile(r"\bwhat\s+pets?\s+did\s+pam\s+have\b", re.I), ("pam", "pets")),
    (re.compile(r"\bpam'?s\s+pets?\b", re.I), ("pam", "pets")),
    # Raised by
    (re.compile(r"\b(who\s+raised\s+pam|who\s+was\s+pam'?s\s+guardian)\b", re.I), ("pam", "raised_by")),
    # Favorites
    (re.compile(r"\b(pam'?s|what\s+is\s+pam'?s)\s+favorite\s+color\b", re.I), ("pam", "favorite color")),
    (re.compile(r"\b(pam'?s|what\s+is\s+pam'?s)\s+favorite\s+sport\b", re.I), ("pam", "favorite sport")),
    (re.compile(r"\b(pam'?s|what\s+is\s+pam'?s)\s+comfort\s+show\b", re.I), ("pam", "comfort show")),
]

def quick_qna_route(txt: str) -> Tuple[Optional[str], Optional[str]]:
    t = txt or ""
    for rx, pair in _QA_PATTERNS:
        if rx.search(t):
            return pair
    return (None, None)

# ====================== Memory lookup helpers ======================
def memory_lookup(subject: str, relation: str) -> Optional[str]:
    sub = (subject or "").strip().lower()
    rel = normalize_relation(relation)
    if not (sub and rel):
        return None
    # MemoryStore first
    val = store.recall(sub, rel)
    if val:
        return str(val)
    # try alias keys kept in memory (fallback)
    for alias, canonical in _REL_ALIASES.items():
        if canonical == rel:
            alt = store.recall(sub, alias)
            if alt:
                return str(alt)
    # special: pam facts as last local lookup
    if sub == "pam":
        if rel in PAM_FACTS:
            return PAM_FACTS[rel]
    return None

# ====================== GPT bridge ======================
@lru_cache(maxsize=128)
def gpt_bridge(prompt: str) -> Tuple[bool, str]:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "You are SoNo: calm, concise, and helpful. Prefer short, warm sentences. If no memory is found, answer plainly and factually."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        out = resp.choices[0].message.content.strip()
        return True, out
    except Exception as e:
        return False, f"(GPT error: {e.__class__.__name__})"

# ====================== Main handler ======================
def handle_user_text(user_text: str) -> dict:
    try:
        txt = (user_text or "").strip()
        if not txt:
            return {"ok": False, "source": "guard", "response": "Type something first."}
        if len(txt) > 2000:
            return {"ok": False, "source": "guard", "response": "Too long. Keep it under 2000 chars."}

        # Identity (never GPT)
        ans_id = identity_answer(txt)
        if ans_id:
            return {"ok": True, "source": "identity", "response": ans_id}

        # TEACH (natural)
        sub_t, rel_t, val_t = parse_teach(txt)
        if sub_t and rel_t and val_t:
            store.remember(sub_t, rel_t, val_t)
            return {"ok": True, "source": "teach", "response": f"Got it. I’ll remember: {sub_t.title()} — {rel_t} → {val_t}."}

        # Quick patterns
        sub_q, rel_q = quick_qna_route(txt)

        # Intent parse backup
        try:
            kind, sub_i, rel_i, obj_i = parse_intent(txt)
        except Exception:
            kind, sub_i, rel_i, obj_i = ("ask", None, None, None)

        sub = (sub_q or sub_i or "").strip().lower()
        rel = normalize_relation(rel_q or rel_i or "")

        # Memory-first if we have (sub, rel)
        if sub and rel:
            val = memory_lookup(sub, rel)
            if val:
                s = sub.title()
                r = rel
                v = str(val)
                if r in ("mom", "mother"): out = f"{v} is {s}'s {r}."
                elif r == "full name": out = f"{s}'s full name is {v}."
                elif r == "birthplace": out = f"{s} was born in {v}."
                elif r == "hometown": out = f"{s} grew up in {v}."
                else: out = f"{s}'s {r} is {v}."
                return {"ok": True, "source": "memory", "response": out}

        # If Pam mentioned but no clean (rel), try light pam.txt retrieval before GPT
        low = txt.lower()
        if any(w in low for w in ["pam", "pamela", "ty's mom", "ty’s mom", "tys mom"]) and "sea otter" not in low:
            try:
                snippet = retrieve_pam_answer(txt)
            except Exception:
                snippet = None
            if snippet:
                return {"ok": True, "source": "pam.txt", "response": snippet}

        # GPT fallback
        ok_gpt, reply = gpt_bridge(txt)
        if ok_gpt and reply:
            return {"ok": True, "source": "gpt", "response": reply}

        return {"ok": True, "source": "fallback", "response": "I don’t know yet — tell me and I’ll remember it."}

    except Exception as e:
        return {"ok": False, "source": "error", "response": f"Handler error: {e.__class__.__name__}"}

# ====================== Routes ======================
@app.route("/", methods=["GET"])
def home():
    try:
        return render_template("index.html")
    except Exception:
        return "SoNo server is running."

@app.route("/ask", methods=["POST"])
def ask_general():
    try:
        data = request.get_json(silent=True) or {}
        text = data.get("text") or data.get("q") or ""
        res = handle_user_text(text)
        return jsonify(res)
    except Exception as e:
        return jsonify({"ok": False, "source": "error", "response": f"Route error: {e.__class__.__name__}"}), 500

@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"})

@app.route("/mem/export", methods=["GET"])
def mem_export():
    try:
        if hasattr(store, "export"):
            payload = store.export()
        elif hasattr(store, "_data"):
            payload = store._data # type: ignore
        else:
            payload = {}
        return jsonify({"ok": True, "memory": payload})
    except Exception as e:
        return jsonify({"ok": False, "error": f"{e.__class__.__name__}: {e}"}), 500

# ====================== Main ======================
if __name__ == "__main__":
    # 0.0.0.0 so other devices on your LAN can hit it via <your-lan-ip>:5000
    app.run(host="0.0.0.0", port=5000, debug=True)
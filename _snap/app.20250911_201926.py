# app.py — SoNo (stable server: identity + memory + pam.txt + GPT fallback)
# ------------------------------------------------------------------------
# What this file does:
# 1) Loads .env + OpenAI client
# 2) Boots Flask
# 3) Preloads:
# - data/pam.txt → key facts (e.g., birthplace, hometown, full name)
# - *_profile.json files from /data → MemoryStore
# (also mirrors "mom" under subject "ty" so “Who is Ty’s mom?” works)
# 4) Answers flow (in order):
# - Identity answers (never GPT)
# - Memory-first (MemoryStore + pam.txt aliases)
# - Pam text retriever (retriever_pam.py)
# - GPT fallback
# 5) Routes:
# - POST /ask (main) + aliases: /ask_v2, /ask/general
# - GET /ask (hint for browsers)
# - GET /mem/export (debug dump of memory)
# - GET /healthz
# - GET /__routes__ (list routes for quick checks)
#
# Notes:
# - Keep debug=True only for local development.
# - If anything breaks, hit /__routes__ and /mem/export to inspect.

from __future__ import annotations

import os
import re
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, Any, Dict

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template

# --- Local modules (your repo) ---
from memory_store import MemoryStore # must expose .remember(), .recall(), .export() or ._data
from intent import parse_intent # returns (kind, subject, relation, object) or raises
from profiles import load_profiles # not used directly now but kept for compatibility
from ingest_pam import load_pam_facts # returns dict of pam facts
from retriever_pam import retrieve_pam_answer # returns short snippet string or None
from normalize import normalize_text as norm # basic text cleanup

# --- OpenAI client (new SDK) ---
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ========== logging ==========
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("sono")

# ========== app + memory ==========
app = Flask(__name__)
store = MemoryStore()

# Small helper for safe console traces without breaking server
def _trace(*items): 
    try: print("TRACE:", *items, flush=True)
    except Exception: pass

# ========== Identity (SoNo speaks for himself) ==========
IDENTITY = {
    "name": "SoNo",
    "creators": "Ty Butler and New Chapter Media Group",
    "mission": "to be a calm, helpful companion for Pam—listening, remembering, and giving clear answers."
}

def identity_answer(text: str) -> Optional[str]:
    t = (text or "").lower()
    if any(p in t for p in ["who are you", "what are you", "tell me about yourself"]):
        return f"I'm {IDENTITY['name']}, created by {IDENTITY['creators']}. My mission is {IDENTITY['mission']}."
    if any(p in t for p in ["your name", "what is your name", "what's your name"]):
        return f"My name is {IDENTITY['name']}."
    if any(p in t for p in ["who created you", "who made you"]):
        return f"I was created by {IDENTITY['creators']}."
    if any(p in t for p in ["your mission", "what is your mission", "what's your mission"]):
        return f"My mission is {IDENTITY['mission']}."
    return None

# ========== Preload data (pam.txt + *_profile.json) ==========
PAM_FACTS: Dict[str, str] = {}

def _preload_pam_txt():
    global PAM_FACTS
    try:
        facts = load_pam_facts(Path("data/pam.txt")) or {}
        # normalize + mirror mom fact under ty
        for k, v in facts.items():
            rel = str(k or "").strip().lower()
            val = str(v or "").strip()
            if not rel or not val:
                continue
            if rel == "mom": # “Who is Ty’s mom?”
                store.remember("ty", "mom", val)
            else:
                store.remember("pam", rel, val)
        PAM_FACTS = {str(k).strip().lower(): str(v).strip() for k, v in facts.items() if str(v).strip()}
        log.info(f"Pam facts preloaded: {len(PAM_FACTS)}")
    except Exception as e:
        log.warning(f"PAM preload skipped: {e.__class__.__name__}: {e}")

def _seed_profile(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            prof = json.load(f)
        sub = str(prof.get("subject", "")).strip().lower()
        facts = prof.get("facts") or {}
        if not (sub and isinstance(facts, dict)):
            return
        for rel, obj in facts.items():
            r = str(rel or "").strip().lower()
            v = str(obj or "").strip()
            if r and v:
                store.remember(sub, r, v)
        log.info(f"Profile loaded: {path.name} ({len(facts)} facts)")
    except Exception as e:
        log.warning(f"Profile load failed for {path.name}: {e.__class__.__name__}: {e}")

def _preload_profiles_dir():
    try:
        data_dir = Path("data")
        for p in data_dir.glob("*_profile.json"):
            _seed_profile(p)
    except Exception as e:
        log.warning(f"Profiles preload error: {e.__class__.__name__}: {e}")

_preload_pam_txt()
_preload_profiles_dir()

# ========== Quick patterns (fast lane) ==========
_QA_PATTERNS = [
    # Ty’s mom
    (re.compile(r"\bwho\s+is\s+ty'?s\s+(mom|mother)\b", re.I), ("ty", "mom")),
    (re.compile(r"\bwhat('?s| is)\s+ty'?s\s+mom'?s?\s+name\b", re.I), ("ty", "mom")),

    # Pam full name
    (re.compile(r"\bwhat('?s| is)\s+pam'?s\s+full\s+name\b", re.I), ("pam", "full name")),
    (re.compile(r"\bwhat\s+is\s+the\s+full\s+name\s+of\s+pam\b", re.I), ("pam", "full name")),

    # Birthplace
    (re.compile(r"\bwhere\s+was\s+pam\s+born\b", re.I), ("pam", "birthplace")),
    (re.compile(r"\bwhen\s+and\s+where\s+was\s+pam\s+born\b", re.I), ("pam", "birthplace")),

    # Hometown / raised / from / grow up
    (re.compile(r"\bwhere\s+(did|was)\s+pam\s+(grow\s*up|raised)\b", re.I), ("pam", "hometown")),
    (re.compile(r"\bwhere\s+is\s+pam\s+from\b", re.I), ("pam", "hometown")),
    (re.compile(r"\bwhat'?s\s+pam'?s\s+hometown\b", re.I), ("pam", "hometown")),

    # Schools
    (re.compile(r"\bwhich\s+schools?\s+did\s+pam\s+attend\b", re.I), ("pam", "schools")),
    (re.compile(r"\bwhere\s+did\s+pam\s+go\s+to\s+school\b", re.I), ("pam", "schools")),

    # Pets
    (re.compile(r"\b(did|does)\s+pam\s+have\s+pets?\b", re.I), ("pam", "pets")),
    (re.compile(r"\bwhat\s+pets?\s+did\s+pam\s+have\b", re.I), ("pam", "pets")),
]

def quick_qna_route(txt: str) -> Tuple[Optional[str], Optional[str]]:
    for rx, pair in _QA_PATTERNS:
        if rx.search(txt):
            return pair
    return (None, None)

# ========== Memory helpers ==========
_REL_ALIASES = {
    "name": "full name",
    "full_name": "full name",
    "birth place": "birthplace",
    "birth_place": "birthplace",
    "where born": "birthplace",
    "where raised": "hometown",
    "home": "hometown",
    "mother": "mom",
}

def _alias(rel: str) -> str:
    r = (rel or "").strip().lower()
    return _REL_ALIASES.get(r, r)

def memory_lookup(sub: str, rel: str) -> Optional[str]:
    sub_n = (sub or "").strip().lower()
    rel_n = _alias(rel)
    if not (sub_n and rel_n):
        return None
    # MemoryStore first
    v = store.recall(sub_n, rel_n)
    if v:
        return str(v)
    # pam.txt mirror (a few common keys)
    if sub_n == "pam":
        if rel_n in PAM_FACTS:
            return PAM_FACTS[rel_n]
        # try alias mapping into pam facts
        rel_a = _REL_ALIASES.get(rel_n)
        if rel_a and rel_a in PAM_FACTS:
            return PAM_FACTS[rel_a]
    return None

def format_memory_sentence(sub: str, rel: str, val: str) -> str:
    s = sub.title()
    r = _alias(rel)
    v = str(val)
    if r in ("mom", "mother"):
        return f"{v} is {s}'s {r}."
    if r == "full name":
        return f"{s}'s full name is {v}."
    if r == "birthplace":
        return f"{s} was born in {v}."
    if r == "hometown":
        return f"{s} grew up in {v}."
    return f"{s}'s {r} is {v}."

# ========== GPT bridge ==========
def gpt_bridge(prompt: str) -> Tuple[bool, str]:
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system",
                 "content": "You are SoNo: calm, concise, helpful. If memory didn’t answer, answer normally and factually."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        out = (resp.choices[0].message.content or "").strip()
        return True, out
    except Exception as e:
        log.error(f"GPT error: {e}")
        return False, f"(GPT error: {e.__class__.__name__})"

# ========== Main handler ==========
def handle_user_text(user_text: str) -> Dict[str, Any]:
    """
    Router:
      1) Guards
      2) Identity (never GPT)
      3) Quick regex → memory
      4) Intent parse backup → memory
      5) Pam retriever
      6) GPT fallback
    """
    try:
        txt_raw = user_text or ""
        txt = norm(txt_raw).strip()
        if not txt:
            return {"ok": False, "source": "guard", "response": "Type something first."}
        if len(txt) > 2000:
            return {"ok": False, "source": "guard", "response": "Too long. Keep it under 2000 chars."}

        # Identity
        ans_id = identity_answer(txt)
        if ans_id:
            return {"ok": True, "source": "identity", "response": ans_id}

        # Quick patterns
        sub, rel = quick_qna_route(txt)

        # Intent parser as backup subject/relation extractor
        try:
            kind, sub_i, rel_i, _obj = parse_intent(txt)
        except Exception:
            kind, sub_i, rel_i, _obj = ("ask", None, None, None)

        sub = (sub or sub_i or "").strip().lower()
        rel = (rel or rel_i or "").strip().lower()

        # Memory-first
        if sub and rel:
            m = memory_lookup(sub, rel)
            if m:
                return {"ok": True, "source": "memory", "response": format_memory_sentence(sub, rel, m)}

        # If Pam is mentioned but relation unclear, try light assist
        low = txt.lower()
        if any(w in low for w in ["pam", "pamela", "ty's mom", "ty’s mom", "tys mom", "mom", "mother"]):
            # heuristic relation guess
            if "full name" in low or ("name" in low and "mom" not in low):
                rel_try = "full name"
            elif "born" in low:
                rel_try = "birthplace"
            elif "raised" in low or "grow up" in low or "from" in low:
                rel_try = "hometown"
            else:
                rel_try = ""
            if rel_try:
                m2 = memory_lookup("pam", rel_try)
                if m2:
                    return {"ok": True, "source": "memory", "response": format_memory_sentence("pam", rel_try, m2)}

            # retrieval from pam.txt (semantic or keyword snippet)
            try:
                snippet = retrieve_pam_answer(txt)
                if snippet:
                    return {"ok": True, "source": "pam.txt", "response": snippet}
            except Exception as e:
                log.warning(f"pam retriever error: {e.__class__.__name__}: {e}")

        # GPT fallback
        ok_gpt, reply = gpt_bridge(txt)
        if ok_gpt and reply:
            return {"ok": True, "source": "gpt", "response": reply}

        return {"ok": True, "source": "fallback", "response": "I don’t know yet — tell me and I’ll remember it."}

    except Exception as e:
        return {"ok": False, "source": "error", "response": f"Handler error: {e.__class__.__name__}"}

# ========== Routes ==========
@app.route("/", methods=["GET"])
def home():
    try:
        return render_template("index.html")
    except Exception:
        return "SoNo server is running."

# Accept ALL old endpoints (UI compatibility)
@app.post("/ask")
@app.post("/ask_v2")
@app.post("/ask/general")
def ask_route():
    try:
        data = request.get_json(force=True) or {}
        text = (data.get("text") or data.get("q") or "").strip()
        result = handle_user_text(text)
        return jsonify(result), 200
    except Exception as e:
        log.exception("ask route failed")
        return jsonify({"ok": False, "source": "error",
                        "response": f"Route error: {e.__class__.__name__}"}), 500

# Hitting /ask in a browser gives a hint, not a 404
@app.get("/ask")
def ask_get_hint():
    return jsonify({"ok": True, "hint": 'POST JSON to /ask with {"text": "your question"}'}), 200

@app.get("/healthz")
def healthz():
    return jsonify({"status": "ok"})

@app.get("/mem/export")
def mem_export():
    """Dump memory for quick sanity checks."""
    try:
        if hasattr(store, "export"):
            payload = store.export()
        elif hasattr(store, "_data"):
            payload = store._data # type: ignore[attr-defined]
        else:
            payload = {}
        # If empty, provide a tiny sample so you can “see” it working
        if not payload:
            sample = {
                "pam": {
                    "full name": store.recall("pam", "full name"),
                    "birthplace": store.recall("pam", "birthplace"),
                    "hometown": store.recall("pam", "hometown"),
                },
                "ty": {"mom": store.recall("ty", "mom")},
            }
            return jsonify({"ok": True, "memory": payload, "sample": sample})
        return jsonify({"ok": True, "memory": payload})
    except Exception as e:
        return jsonify({"ok": False, "error": f"{e.__class__.__name__}: {e}"}), 500

@app.get("/__routes__")
def _routes():
    return jsonify(sorted(str(r) for r in app.url_map.iter_rules()))

# ========== Main ==========
if __name__ == "__main__":
    # HOST=0.0.0.0 lets your phone/other PC on the LAN connect: http://<LAN-IP>:5000
    app.run(host="0.0.0.0", port=5000, debug=True)
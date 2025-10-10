# app.py — SoNo (solid build: identity-first, natural teach/recall, pam preload, GPT fallback)
# -------------------------------------------------------------------------------------------
# What this server does (stable order):
# 1) Identity answers (NEVER GPT)
# 2) Teach via commands + natural statements (stores into MemoryStore)
# 3) Memory-first recall (pronouns + fuzzy relations)
# 4) Pam retrieval/summary from pam facts (if mentioned)
# 5) GPT fallback (guarded not to contradict identity/memory)
# 6) Persistence: loads from memory_store.json, pam_facts_flat.json, pam_facts_flat.json
# 7) Routes: /, /ask (POST + GET hint), /mem/export, /mem/import, /healthz, /tests/smoke
# -------------------------------------------------------------------------------------------

from __future__ import annotations

import os, re, json, time, sys
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from difflib import SequenceMatcher
from collections import deque, Counter
from datetime import datetime

# 🧠 Force include project root for local imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# ✅ Core memory module
from memory_store import MemoryStore

# ✅ Flask + environment setup
from flask import Flask, request, jsonify, send_file, render_template, make_response, Response
from dotenv import load_dotenv

# ✅ Load environment variables
load_dotenv()



# ------------------------------
# Render Disk Debug Check
# ------------------------------
print("DEBUG: Files in /data ->", os.listdir("/data") if os.path.exists("/data") else "NO /data DIRECTORY FOUND")


memory = MemoryStore()
MODE = "closed_test"



# --------------------------------------------------------
# Closed Test Operations Logger + Decorator
# (must appear before any @track_activity(...) usage)
# --------------------------------------------------------
import threading
from datetime import datetime

ACTIVITY_LOG_FILE = "test_activity_log.json"
_activity_lock = threading.Lock()

def _append_json_list(path: str, entry: dict):
    """Append an entry to a JSON list file (thread-safe)."""
    try:
        with _activity_lock:
            data = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f) or []
                    except Exception:
                        data = []
            data.append(entry)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[ActivityLogError] {e}")

def log_activity(tester: str, route: str, status: str = "success", note: str = ""):
    """Log a single activity event."""
    entry = {
        "tester": tester or "unknown",
        "route": route,
        "status": status,
        "note": note,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    _append_json_list(ACTIVITY_LOG_FILE, entry)

def track_activity(route_name: str):
    """Decorator to log activity for a route."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            who = "unknown"
            try:
                if request.is_json:
                    payload = request.get_json(silent=True) or {}
                    # prefer explicit tester key/name if present
                    who = payload.get("key") or payload.get("tester") or "unknown"
                else:
                    who = request.args.get("tester", "unknown")
            except Exception:
                who = "unknown"

            resp = func(*args, **kwargs)
            try:
                log_activity(who, route_name, "success")
            except Exception as e:
                print(f"[track_activity] log failed: {e}")
            return resp
        wrapper.__name__ = func.__name__  # keep Flask endpoint name stable
        return wrapper
    return decorator



# --------------------------------------------------------
# Auto Memory Sanitization on Startup
# --------------------------------------------------------
try:
    print("[Startup] Running automatic memory sweep...")
    memory.sanitize_all()
    print("[Startup] ✅ Memory successfully sanitized at launch.")
except Exception as e:
    print(f"[Startup] ⚠️ Auto-sweep failed: {e}")



# ------------------ AUTO-INTENT + TONE DETECTION ------------------
import re

def detect_emotion_and_tone(text: str) -> str:
    """
    Lightweight tone + intent detector for SoulNode.
    Analyzes user phrasing and keywords to classify the emotional tone or intent.
    Returns one of: 'cheeky', 'motivational', 'reflective', 'legacy', 'focus', or None.
    """
    if not text:
        return None

    t = text.lower().strip()

    # Cheeky / playful language
    if any(x in t for x in ["haha", "lol", "you thought", "funny", "😂", "🤣"]):
        return "cheeky"

    # Motivational intent
    if any(x in t for x in ["let's go", "we got this", "i can do this", "stay focused", "rise", "push through"]):
        return "motivational"

    # Reflective / introspective phrasing
    if any(x in t for x in ["i feel", "sometimes", "i've been thinking", "why does", "it hurts", "reflecting"]):
        return "reflective"

    # Legacy / family / purpose tone
    if any(x in t for x in ["my kids", "my legacy", "for my mom", "for my family", "future", "generation", "purpose"]):
        return "legacy"

    # Focus / discipline tone
    if any(x in t for x in ["stay sharp", "focus", "locked in", "no distractions", "grind mode", "beast mode"]):
        return "focus"

    # If none matched, return None
    return None
# ------------------------------------------------------------------



# ---------------- SoulNode Identity Preload ----------------
try:
    preload_data = {
        "name": "SoulNode",
        "creator": "Ty Butler",
        "mission": "To learn, heal, and help build New Chapter Media’s legacy.",
        "origin": "New Chapter Media Group",
        "type": "AI co-pilot"
}

    # Prevent redundant memory saves during preload
    for key, val in preload_data.items():
        if not memory.memory.get("solnode", {}).get(key):
            memory.remember("solnode", key, val, silent=True)

    print("[Identity] ✅ SoulNode identity preloaded into memory (clean mode)")


except Exception as e:
    print(f"[Identity] ⚠️ Failed to preload SoulNode identity: {e}")






# ---- PAM relation resolver + memory answer helper ---------------------------
import re
from typing import Dict, List, Optional

REL_ALIASES: Dict[str, str] = {
    # names / identity
    "full name": "full_name", "fullname": "full_name", "name": "full_name",
    "who is pam": "identity", "who are you": "identity", "creator": "identity",
    "mission": "identity",
    # places
    "birthplace": "birthplace", "born": "birthplace", "hometown": "birthplace",
    "where from": "birthplace", "where is she from": "birthplace",
    # family
    "mother": "mother", "father": "father", "parents": "parents",
    "brother": "siblings", "sister": "siblings", "siblings": "siblings",
    "kids": "children", "children": "children", "grandkids": "grandchildren",
    # pets
    "pet": "pets", "pets": "pets", "dog": "pets", "breed": "pets", "yasha": "pets",
    # school / work
    "school": "schools", "schools": "schools", "education": "schools",
    "job": "occupation", "work": "occupation", "first job": "occupation",
    # misc buckets from your dataset
    "values": "values", "health": "health", "prayer": "prayer warriors",
    "restaurants": "restaurants", "meals": "meals", "tradition": "tradition",
    "style": "style", "music": "music",
}

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()

def _resolve_relation(question: str) -> str:
    t = _norm(question)
    # High-signal keywords first
    if "full name" in t or ("name" in t and "pam" in t):
        return "full_name"
    if any(k in t for k in ["yasha", "breed", "dog", "pet", "pets"]):
        return "pets"
    if any(k in t for k in ["hometown", "born", "birthplace", "where from"]):
        return "birthplace"

    # Alias table fallback: pick the first alias that appears
    for key, rel in REL_ALIASES.items():
        if key in t:
            return rel

    # Last resort
    return "fact"

def answer_from_pam_memory(question: str, store) -> Optional[dict]:
    """
    Ask MemoryStore for the best value given the resolved relation.
    `store` is your MemoryStore instance used elsewhere in app.py.
    Returns a response dict or None if no match.
    """
    rel = _resolve_relation(question)
    # MemoryStore may expose different getters; support both common shapes:

    # Option A: nested dict store[subject][relation] -> [values...]
    try:
        vals = store.get("pam", rel) # if you implemented get(subject, relation)
        if isinstance(vals, list) and vals:
            vals = sorted(vals, key=len, reverse=True) # prefer fuller answer
            return {"ok": True, "response": vals[0], "source": "pam_facts_flat.json"}
        if isinstance(vals, str) and vals:
            return {"ok": True, "response": vals, "source": "pam_facts_flat.json"}
    except Exception:
        pass

    # Option B: search API store.find(subject, relation)
    try:
        vals = store.find("pam", rel) # if you implemented find()
        if isinstance(vals, list) and vals:
            vals = sorted(vals, key=len, reverse=True)
            return {"ok": True, "response": vals[0], "source": "pam_facts_flat.json"}
        if isinstance(vals, str) and vals:
            return {"ok": True, "response": vals, "source": "pam_facts_flat.json"}
    except Exception:
        pass

    return None
# ------------------------------------------------------------------------------

# ---- Optional GPT (only used if OPENAI_API_KEY is set) ----
import os
from dotenv import load_dotenv

# Load environment variables (works locally and safely ignored in Render)
load_dotenv()

# Fetch API key and model
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

# ✅ Validate key (safe for local + Render)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

if not OPENAI_API_KEY:
    print("⚠️  Warning: No OPENAI_API_KEY detected — running in local safe mode.")
    OPENAI_API_KEY = "dummy_key_for_local_dev"  # fallback for local dev

# ✅ Initialize OpenAI client (non-blocking)
try:
    from openai import OpenAI
    _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    print("✅ OpenAI client initialized.")
except Exception as e:
    print("⚠️  OpenAI init error:", e)
    _openai_client = None


# ---- Local modules (with safe fallbacks for utils) ----
try:
    from ingest_pam import load_pam_facts as _load_pam_txt
except Exception:
    _load_pam_txt = None

try:
    from utils import save_memory as _save_memory, log_unknown_input as _log_unknown_input
except Exception:
    def _save_memory(*_a, **_k): pass
    def _log_unknown_input(*_a, **_k): pass

# ------------------------------------------------------------
# 🧠 SANDBOX ISOLATION LAYER - Multi-Tester Environment (v1.3 Semantic Integrated)
# ------------------------------------------------------------
import threading
import json
import os
import re
import math
from flask import request, jsonify, render_template

# ✅ Thread-local tester context
_active_tester = threading.local()
_active_tester.name = None

# ==== Semantic Matching (Embeddings) helpers ====
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def _cosine(u, v):
    if not u or not v or len(u) != len(v):
        return -1.0
    dot = sum(a * b for a, b in zip(u, v))
    nu = math.sqrt(sum(a * a for a in u))
    nv = math.sqrt(sum(b * b for b in v))
    return dot / (nu * nv) if nu and nv else -1.0

def _embed(text: str):
    """Return embedding vector using OpenAI embeddings API."""
    try:
        if '_openai_client' in globals() and _openai_client:
            resp = _openai_client.embeddings.create(
                model=EMBED_MODEL,
                input=text
            )
            return resp.data[0].embedding
    except Exception as e:
        print(f"[Embed ERROR] {e}")
    return None

# ==== Tester Isolation ====
TESTER_PROFILES = {
    "tester1": "/data/memory_tester_1.json",
    "tester2": "/data/memory_tester_2.json",
    "tester3": "/data/memory_tester_3.json",
    "tester4": "/data/memory_tester_4.json",
}

def _get_sandbox_path(tester_id: str):
    tester_id = tester_id.lower().strip()
    path = TESTER_PROFILES.get(tester_id)
    if not path:
        raise ValueError(f"Unknown tester ID: {tester_id}")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path

def _load_sandbox_memory(path: str):
    """Ensure JSON structure: {'data': {}, '_index': {}}"""
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            print(f"[Sandbox] Load failed ({path}): {e}")
            raw = {}
    else:
        raw = {}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(raw, f)

    if not isinstance(raw, dict):
        raw = {}
    return {
        "data": raw.get("data", {}),
        "_index": raw.get("_index", {})
    }

def _save_sandbox_memory(path: str, mem: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(mem, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Sandbox] Save failed ({path}): {e}")

# ==== Flask Setup ====
@app.before_request
def _set_active_tester():
    tester_id = request.headers.get("X-Tester-ID") or request.args.get("tester")
    _active_tester.name = tester_id.lower().strip() if tester_id else None

@app.route("/sandbox")
def sandbox_page():
    tester = request.args.get("tester", "tester1")
    return render_template("sandbox.html", tester=tester)

@app.route("/sandbox/ask", methods=["POST"])
def sandbox_ask():
    """Handles isolated tester memory with full semantic recall."""
    try:
        tester = _active_tester.name or "tester1"
        path = _get_sandbox_path(tester)
        mem = _load_sandbox_memory(path)
        store, index = mem["data"], mem["_index"]

        data = request.get_json(silent=True) or {}
        text = _norm(data.get("text", ""))

        if not text:
            return jsonify({"ok": False, "error": "Empty input"})

        answer = None

        # 🧠 Remember
        if text.startswith("remember"):
            match = re.match(r"remember\s+(?:that\s+)?(?:my\s+)?(.+?)\s+is\s+(.+)", text)
            if match:
                key, value = match.groups()
                key_n = _norm(key)
                emb = _embed(key_n)
                store[key_n] = value
                if emb:
                    index[key_n] = {"e": emb}
                mem["data"], mem["_index"] = store, index
                _save_sandbox_memory(path, mem)
                answer = f"Got it. I’ll remember your {key} is {value}."
            else:
                answer = "Try saying: 'Remember my car is Tesla.'"

        # 🧠 Recall (semantic + fuzzy)
        elif any(word in text for word in ["what", "who", "where", "favorite", "tell", "do you know", "which"]):
            q = re.sub(r"^(what|who|where|tell|which|favorite|do you know)\s+", "", text)
            q_n = _norm(q.replace("my ", "").replace("the ", ""))

            # 1️⃣ Direct hit
            if q_n in store:
                answer = store[q_n]

            # 2️⃣ Semantic search
            if not answer and index:
                q_emb = _embed(q_n)
                if q_emb:
                    best_key, best_score = None, -1.0
                    for k, meta in index.items():
                        emb = meta.get("e")
                        if emb:
                            s = _cosine(q_emb, emb)
                            if s > best_score:
                                best_key, best_score = k, s
                    if best_key and best_score >= 0.78:
                        answer = store.get(best_key)

            # 3️⃣ Fuzzy fallback
            if not answer and store:
                from difflib import SequenceMatcher
                best_key, best_score = None, 0.0
                for k in store.keys():
                    s = SequenceMatcher(None, q_n, k).ratio()
                    if s > best_score:
                        best_key, best_score = k, s
                if best_key and best_score >= 0.62:
                    answer = store[best_key]

            if not answer:
                answer = f"I don’t know your {q_n} yet."

        else:
            answer = "Sandbox active. Use 'Remember my car is Tesla' or 'What is my car?'"

        return jsonify({"ok": True, "tester": tester, "answer": answer})

    except Exception as e:
        print(f"[Sandbox ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)})





    
    # ------------------------------------------------------------
# 🧩 SANDBOX UI - Lightweight Test Console
# ------------------------------------------------------------
@app.route("/sandbox_ui", methods=["GET"])
def sandbox_ui():
    """Simple HTML UI for sandbox testing."""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>🧠 SoulNode Sandbox</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0d1117; color: #eee; display:flex; flex-direction:column; align-items:center; margin-top:40px; }
            input, select, button { font-size:16px; padding:8px; border-radius:6px; border:none; margin:4px; }
            input { width:320px; }
            select { background:#161b22; color:#eee; }
            button { background:#238636; color:white; cursor:pointer; }
            button:hover { background:#2ea043; }
            #log { width:480px; background:#161b22; border-radius:10px; padding:12px; margin-top:20px; min-height:180px; overflow-y:auto; }
            .msg { margin:8px 0; }
            .tester { color:#58a6ff; }
            .ai { color:#c9d1d9; }
        </style>
    </head>
    <body>
        <h2>🧠 SoulNode Sandbox Console</h2>
        <div>
            <label>Tester:</label>
            <select id="tester">
                <option value="tester1">tester1</option>
                <option value="tester2">tester2</option>
                <option value="tester3">tester3</option>
                <option value="tester4">tester4</option>
            </select>
            <input id="input" placeholder="Type a prompt (e.g., Remember my favorite snack is trail mix.)" />
            <button onclick="send()">Send</button>
        </div>
        <div id="log"></div>

        <script>
            async function send() {
                const tester = document.getElementById('tester').value;
                const text = document.getElementById('input').value.trim();
                if (!text) return;
                append('You', text);
                const res = await fetch('/sandbox/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-Tester-ID': tester },
                    body: JSON.stringify({ text })
                });
                const data = await res.json();
                append('SoulNode', data.answer || '[No response]');
                document.getElementById('input').value = '';
            }

            function append(sender, msg) {
                const log = document.getElementById('log');
                const div = document.createElement('div');
                div.className = 'msg';
                div.innerHTML = `<span class="${sender==='You'?'tester':'ai'}"><b>${sender}:</b> ${msg}</span>`;
                log.appendChild(div);
                log.scrollTop = log.scrollHeight;
            }
        </script>
    </body>
    </html>
    """



# -------------------------------------------------------------------------------------------
# Identity (NEVER GPT)
# -------------------------------------------------------------------------------------------
IDENTITY = {
    "name": "SoNo",
    "creators": "Ty Butler / NCMG",
    "mission": "steady, helpful memory for Pam—clear answers without drama.",
}

_CREATOR_WORDS = {"created","built","made","developed","invented","creator","founded"}
_CREATOR_NAMES = {"ty","ty butler","ncmg","butler","openai"}
_ID_PURPOSE = {"purpose","role","job","mission","why are you here","why do you exist","what do you do"}

def identity_answer(text: str) -> Optional[str]:
    t = (text or "").lower().replace("’","'").strip()
    if any(p in t for p in ("who are you","what are you","tell me about yourself","your name","what is your name","what's your name")):
        if "name" in t:
            return f"My name is {IDENTITY['name']}."
        return f"I’m {IDENTITY['name']}, created by {IDENTITY['creators']}. My mission is {IDENTITY['mission']}"
    if any(p in t for p in _ID_PURPOSE):
        return f"My mission is {IDENTITY['mission']}"
    if "who created you" in t or "who made you" in t or "who developed you" in t \
       or any(w in t for w in _CREATOR_WORDS) or any(n in t for n in _CREATOR_NAMES) \
       or "you were created by" in t or "if ty built you" in t or "if ty created you" in t:
        return f"I was created by {IDENTITY['creators']}."
    if "your hometown" in t:
        return "I don’t have a hometown — I’m software. My mission is steady, helpful memory for Pam."
    return None

# -------------------------------------------------------------------------------------------
# Memory store + helpers (no dependency on store.search)
# -------------------------------------------------------------------------------------------
store = MemoryStore()

REL_ALIASES: Dict[str, str] = {
    # names
    "name":"full name","full_name":"full name",
    # birth/home
    "birth place":"birthplace","where born":"birthplace","born":"birthplace",
    "home":"hometown","home town":"hometown","where from":"hometown","raised":"hometown","grow up":"hometown","grown up":"hometown",
    # family
    "mother":"mom",
    # favorites / comfort
    "favourite color":"favorite color","fav color":"favorite color","colour":"favorite color",
    "favorite show":"comfort show","comfort tv":"comfort show","tv comfort":"comfort show",
    "favorite snack":"comfort snack","comfort snacks":"comfort snack","snack":"comfort snack",
    # misc
    "education":"schools","school":"schools",
    "doc":"doctor","physician":"doctor",
    "cell":"phone","mobile":"phone","telephone":"phone",
}
_CANON_REL = {
    "full name","birthplace","hometown","mom","favorite color","comfort show","comfort snack",
    "pets","schools","meds","allergies","doctor","emergency contact","phone","church","middle name",
}

def _best_rel_match(r: str) -> str:
    r = (r or "").strip().lower().replace("_"," ")
    r = REL_ALIASES.get(r, r)
    if r in _CANON_REL: return r
    best, score = r, 0.0
    for cand in _CANON_REL.union(set(REL_ALIASES.values())):
        s = SequenceMatcher(None, r, cand).ratio()
        if s > score: best, score = cand, s
    return best if score >= 0.68 else r

def _norm_sub(s: str) -> str:
    s = (s or "").strip().lower()
    if s.endswith("’s") or s.endswith("'s"): s = s[:-2]
    return s

def mem_recall(sub: str, rel: str) -> Optional[str]:
    try:
        return store.recall(_norm_sub(sub), _best_rel_match(rel))
    except Exception:
        return None

def mem_remember(sub: str, rel: str, val: str) -> None:
    try:
        store.remember(_norm_sub(sub), _best_rel_match(rel), (val or "").strip())
        # try to persist safely if MemoryStore exposes save()
        if hasattr(store, "save"):
            try: store.save()
            except Exception as e: print("store.save error:", e)
    except Exception as e:
        print("memory remember error:", e)

def mem_forget(sub: str, rel: str) -> bool:
    try:
        ok = bool(store.forget(_norm_sub(sub), _best_rel_match(rel)))
        if ok and hasattr(store, "save"):
            try: store.save()
            except Exception as e: print("store.save error:", e)
        return ok
    except Exception:
        return False

# -------------------------------------------------------------------------------------------
# Preload: memory_store.json (any shape), pam_facts_flat.json, pam_facts_flat.json
# -------------------------------------------------------------------------------------------
def _load_memory_store_json(p: Path) -> int:
    if not p.exists(): return 0
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("[MemoryStore] Failed to load", p.name, ":", e)
        return 0

    added = 0
    try:
        if isinstance(raw, dict):
            # dict-of-dicts {sub: {rel: val}}
            for sub, rels in raw.items():
                if not isinstance(rels, dict): continue
                for rel, val in rels.items():
                    mem_remember(str(sub), str(rel), str(val)); added += 1
        elif isinstance(raw, list):
            # list of triples/objs
            for item in raw:
                if isinstance(item, dict) and all(k in item for k in ("sub","rel","val")):
                    mem_remember(item["sub"], item["rel"], item["val"]); added += 1
                elif isinstance(item, (list, tuple)) and len(item) >= 3:
                    sub, rel, val = item[0], item[1], item[2]
                    mem_remember(str(sub), str(rel), str(val)); added += 1
        else:
            print("[MemoryStore] Unsupported JSON shape in", p.name)
    except Exception as e:
        print("[MemoryStore] Ingest error:", e)

    return added

def _load_pam_flat(p: Path) -> int:
    if not p.exists(): return 0
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print("[pam_facts_flat] load error:", e); return 0

    facts = []
    if isinstance(doc, dict) and isinstance(doc.get("facts"), list):
        facts = doc["facts"]
    elif isinstance(doc, list):
        facts = doc
    else:
        print("[pam_facts_flat] unexpected shape; expected list or {'facts': [...]}"); return 0

    added = 0
    for item in facts:
        if not isinstance(item, dict): continue
        sub = str(item.get("sub","pam")).strip() or "pam"
        rel = str(item.get("rel","")).strip()
        val = str(item.get("val","")).strip()
        if rel and val:
            mem_remember(sub, rel, val); added += 1
    return added

# rename this function:
def _load_pam_txt_file(p: Path) -> int:
    if not (p and p.exists() and _load_pam_txt): 
        return 0
    try:
        facts = _load_pam_txt(p) # this now refers to the imported loader
    except Exception as e:
        print("pam_facts_flat.json parse error:", e); return 0
    added = 0
    if isinstance(facts, dict):
        for rel, val in facts.items():
            if not str(val).strip(): 
                continue
            mem_remember("pam", str(rel), str(val)); added += 1
    return added

pre_added = _load_memory_store_json(MEM_FILE)
pre_added += _load_memory_store_json(SESSION_FILE)
pre_added += _load_pam_flat(PAM_JSON)
pre_added += _load_pam_txt_file(PAM_TXT)
print(f"[app] Preloaded facts into memory: {pre_added}")

# -------------------------------------------------------------------------------------------
# Teach parsing (commands + natural)
# -------------------------------------------------------------------------------------------
_last_q_rel: Optional[Tuple[str,str]] = None

DISCARD_PREFIXES = re.compile(r"^(?:actually|ok|okay|so|well|listen|correction|update)[,:\- ]+\s*", re.I)
def _strip_discards(s: str) -> str:
    return DISCARD_PREFIXES.sub("", (s or "").strip())

PRONOUNS = {
    "her":"pam","she":"pam","mom":"pam","mother":"pam",
    "him":"ty","he":"ty","dad":"ty","father":"ty",
    "me":"ty","my":"ty","i":"ty",
}

def resolve_profile_subject(profile: str) -> str:
    return "ty" if (profile or "ty").strip().lower()=="ty" else "pam"

def resolve_subject_token(tok: str, profile: str) -> str:
    tok = (tok or "").lower()
    if tok in PRONOUNS: return PRONOUNS[tok]
    if tok in {"me","my","i"}: return "ty"
    if tok in {"she","her","mom","mother"}: return "pam"
    return _norm_sub(tok)

def fallback_subject(profile: str) -> str:
    if _last_q_rel: return _last_q_rel[0]
    return resolve_profile_subject(profile)

TEACH_CMD = re.compile(
    r"^(?:remember|set|save|update|teach|learn)\s+(?:that\s+|the\s+)?(?P<left>.+?)\s+(?:is|=|to)\s+(?P<val>.+)$",
    re.I,
)

def try_teach_command(raw: str, active_profile: str) -> Optional[str]:
    t = _strip_discards(raw)
    m = TEACH_CMD.match(t)
    if not m: return None
    left, val = m.group("left").strip(), m.group("val").strip()
    msub = re.match(r"^([A-Za-z]+)(?:'s|’s)?\s+(.*)$", left)
    if msub:
        subj = resolve_subject_token(msub.group(1), active_profile)
        rel = _best_rel_match(msub.group(2))
    else:
        subj = fallback_subject(active_profile)
        rel = _best_rel_match(left)

    if subj == "pam" and rel in {"born","where born","birth place"}: rel = "birthplace"
    mem_remember(subj, rel, val)
    _save_memory(store, subj, rel, val) # no-op if utils not present
    return f"Got it — {subj.title()}'s {rel} is {val}."

# Natural statements (NOT questions)
DECL_RXES: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"^([a-z][a-z _-]{1,40})\s+(?:is|=|to)\s+(.+)$", re.I), "REL_FIRST"), # "hometown is LA"
    (re.compile(r"^my\s+(.+?)\s+(?:is|=|to)\s+(.+)$", re.I), "PROFILE"), # "my doctor is Dr Lee"
    (re.compile(r"^([A-Za-z]+)(?:'s|’s)\s+(.+?)\s+(?:is|=|to)\s+(.+)$", re.I), "POSSESSIVE"), # "Pam's doctor is ..."
    (re.compile(r"^([A-Za-z]+)\s+(.+?)\s+(?:is|=|to)\s+(.+)$", re.I), "SUBJ_REL"), # "Pam doctor is ..."
    (re.compile(r"^([A-Za-z]+)\s+(?:was\s+)?(?:born\s+in|birth\s*place|birthplace)\s+(.+)$", re.I), "BORN"),
)

def try_teach_natural(raw: str, active_profile: str) -> Optional[str]:
    t = _strip_discards(raw)
    if t.endswith("?") or re.match(r"^(who|what|where|when|how)\b", t, re.I):
        return None

    for rx, kind in DECL_RXES:
        m = rx.match(t)
        if not m: 
            continue

        if kind == "REL_FIRST":
            sub = fallback_subject(active_profile)
            rel = _best_rel_match(m.group(1))
            val = m.group(2).strip()
        elif kind == "PROFILE":
            sub = resolve_profile_subject(active_profile)
            rel = _best_rel_match(m.group(1))
            val = m.group(2).strip()
        elif kind == "POSSESSIVE":
            sub = resolve_subject_token(m.group(1), active_profile)
            rel = _best_rel_match(m.group(2))
            val = m.group(3).strip()
        elif kind == "SUBJ_REL":
            sub = resolve_subject_token(m.group(1), active_profile)
            rel = _best_rel_match(m.group(2))
            val = m.group(3).strip()
        else: # BORN
            sub = resolve_subject_token(m.group(1), active_profile)
            rel, val = "birthplace", m.group(2).strip()

        if sub == "pam" and rel in {"born","where born","birth place"}: rel = "birthplace"
        mem_remember(sub, rel, val)
        _save_memory(store, sub, rel, val)
        return f"Got it — {sub.title()}'s {rel} is {val}."
    return None

# -------------------------------------------------------------------------------------------
# Recall (messy phrasing, pronouns, fuzzy relations + summaries)
# -------------------------------------------------------------------------------------------
_REL_KEYWORDS: Tuple[Tuple[set, str], ...] = (
    ({"born","birth","birth place","birthplace","where born"}, "birthplace"),
    ({"hometown","home town","from","raised","grow up","grown up"}, "hometown"),
    ({"full name","name"}, "full name"),
    ({"mom","mother"}, "mom"),
    ({"favorite color","favourite color","fav color","colour"}, "favorite color"),
    ({"comfort show","comfort tv","favorite show"}, "comfort show"),
    ({"comfort snack","snack","favorite snack"}, "comfort snack"),
    ({"pets","pet"}, "pets"),
    ({"schools","school","education"}, "schools"),
    ({"phone","cell","mobile","telephone"}, "phone"),
    ({"doctor","doc","physician"}, "doctor"),
)

def _format_memory_sentence(sub: str, rel: str, val: str) -> str:
    s = _norm_sub(sub).title(); r = _best_rel_match(rel); v = str(val)
    if r == "mom": return f"{v} is {s}'s mom."
    if r == "full name": return f"{s}'s full name is {v}."
    if r == "birthplace": return f"{s} was born in {v}."
    if r == "hometown": return f"{s} grew up in {v}."
    return f"{s}'s {r} is {v}."

def _summary_about(sub: str) -> Optional[str]:
    subn = _norm_sub(sub)
    fields = ["full name","birthplace","hometown","favorite color","comfort show","comfort snack","phone","doctor","pets","schools"]
    parts: List[str] = []
    for f in fields:
        v = mem_recall(subn, f)
        if v:
            if f == "full name": parts.append(f"Full name: {v}")
            elif f == "birthplace":parts.append(f"Born in {v}")
            elif f == "hometown": parts.append(f"Hometown: {v}")
            else: parts.append(f"{f.title()}: {v}")
    return ("; ".join(parts) + ".") if parts else None

def loose_recall(text: str, profile: str) -> Optional[Dict[str, str]]:
    global _last_q_rel
    t = (text or "").lower().replace("’","'").strip()
    if not t: return None

    # Possessive: "pam's hometown?" / "her hometown?"
    m = re.search(r"\b([a-z]+)(?:'s|’s)\s+(.+?)\??$", t)
    if m:
        subj_tok = resolve_subject_token(m.group(1), profile)
        rel = _best_rel_match(m.group(2))
        v = mem_recall(subj_tok, rel)
        if v:
            _last_q_rel = (subj_tok, rel)
            return {"ok": True, "source": "memory", "response": _format_memory_sentence(subj_tok, rel, v)}

    # "my hometown?" / "my doctor?" etc
    m2 = re.search(r"^my\s+(.+?)\??$", t)
    if m2:
        subj = resolve_profile_subject(profile)
        rel = _best_rel_match(m2.group(1))
        v = mem_recall(subj, rel)
        if v:
            _last_q_rel = (subj, rel)
            return {"ok": True, "source": "memory", "response": _format_memory_sentence(subj, rel, v)}

    # “what’s her hometown” / “where was she born”
    m3 = re.search(r"^(?:what(?:'s| is)|where(?:'s| is)?|where)\s+(?:her|she)\s+(.+?)\??$", t)
    if m3:
        subj = "pam"
        rel = _best_rel_match(m3.group(1))
        v = mem_recall(subj, rel)
        if v:
            _last_q_rel = (subj, rel)
            return {"ok": True, "source": "memory", "response": _format_memory_sentence(subj, rel, v)}

    # “where was pam born” / “what’s pam’s hometown”
    if "pam" in t:
        for keys, rel in _REL_KEYWORDS:
            if any(k in t for k in keys):
                v = mem_recall("pam", rel)
                if v:
                    _last_q_rel = ("pam", rel)
                    return {"ok": True, "source": "memory", "response": _format_memory_sentence("pam", rel, v)}
        if any(p in t for p in ["tell me something about pam","something about pam","about pam","who is pam"]):
            s = _summary_about("pam")
            if s:
                _last_q_rel = ("pam","summary")
                return {"ok": True, "source": "memory", "response": s}

    # Generic: “tell me something about X”
    m4 = re.search(r"(?:tell me.*about|something about)\s+([a-z]+)$", t)
    if m4:
        subj = resolve_subject_token(m4.group(1), profile)
        s = _summary_about(subj)
        if s:
            _last_q_rel = (subj,"summary")
            return {"ok": True, "source": "memory", "response": s}

    return None

# -------------------------------------------------------------------------------------------
# Pam retrieval/summary (AFTER memory, BEFORE GPT)
# -------------------------------------------------------------------------------------------
def pam_retrieve(q: str) -> Optional[str]:
    try:
        if "pam" not in (q or "").lower(): return None
        s = _summary_about("pam")
        if s: return s
        return "Pam is Ty's mom."
    except Exception as e:
        print("pam retrieve error:", e); return None

# -------------------------------------------------------------------------------------------
# GPT fallback (guarded)
# -------------------------------------------------------------------------------------------
def gpt_answer(prompt: str) -> Optional[str]:
    if not _openai_client: return None
    try:
        # memory guard: add known facts as “context” (light)
        context = []
        for sub in ("pam","ty"):
            facts = store.export().get(sub, {}) if hasattr(store, "export") else {}
            if isinstance(facts, dict):
                context.append(f"{sub}: " + "; ".join(f"{k}={v}" for k,v in facts.items()))
        sys = (
            "You are SoNo. Be concise, steady, kind. "
            "Never contradict explicit identity or memory facts. "
            "If unsure, say you’re not sure."
        )
        msgs = [{"role":"system","content":sys}]
        if context:
            msgs.append({"role":"system","content":"Known facts:\n" + "\n".join(context)})
        msgs.append({"role":"user","content":prompt})

        resp = _openai_client.chat.completions.create(
            model=OPENAI_MODEL, temperature=0.2, max_tokens=350, messages=msgs
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as e:
        print("GPT error:", e); return None

# -------------------------------------------------------------------------------------------
# Telemetry
# -------------------------------------------------------------------------------------------
LAST_EVENTS = deque(maxlen=100)
COUNTS = Counter()
def record_event(q: str, response: str, source: str, ms: float):
    LAST_EVENTS.appendleft({"q": q, "response": response, "source": source, "ms": round(ms,2)})
    COUNTS[source] += 1; COUNTS["_total"] += 1

# -------------------------------------------------------------------------------------------
# Main handler
# -------------------------------------------------------------------------------------------
def handle_question(text: str, profile: str="ty") -> Dict[str, Any]:
    try:
        q = (text or "").strip()
        if not q:
            return {"ok": False, "source": "guard", "response": "Type something first."}
        if len(q) > 4000:
            return {"ok": False, "source": "guard", "response": "Too long. Keep it under 4000 chars."}
                

        # 1) Identity
        ident = identity_answer(q)
        if ident:
            _save_memory(store, "query", "identity", q)
            return {"ok": True, "source": "identity", "response": ident}

        # 2) Teach
        taught = try_teach_command(q, profile) or try_teach_natural(q, profile)
        if taught:
            return {"ok": True, "source": "teach", "response": taught}

        # 3) Memory-first recall
        mem = loose_recall(q, profile)
        if mem:
            return mem

        # 4) Pam retrieval/summary
        pr = pam_retrieve(q)
        if pr:
            return {"ok": True, "source": "pam_facts_flat.json", "response": pr}

        # 5) GPT fallback (optional)
        g = gpt_answer(q)
        if g:
            return {"ok": True, "source": "gpt", "response": g}

        # Unknown
        _log_unknown_input(q)
        return {
            "ok": True, "source": "unknown",
            "response": "Ask me about Pam’s hometown, birthplace, full name, doctor, phone—or teach me more."
        }
    except Exception as e:
        return {"ok": False, "source": "error", "response": f"Handler error: {e.__class__.__name__}"}
    
    # ----------------- Emotion & Tone Engine (SoulNode Personality) -----------------
import random

def detect_emotion_and_tone(text: str) -> str:
    """Lightweight mood detector + SoulNode personality routing."""
    t = text.lower()

    if any(word in t for word in ["sad", "tired", "drained", "alone", "hurt", "lost", "down"]):
        return "reflective"
    elif any(word in t for word in ["happy", "excited", "great", "love", "thank", "joy", "peace"]):
        return "motivational"
    elif any(word in t for word in ["legacy", "dad", "kids", "escalade", "mission", "family"]):
        return "legacy"
    elif any(word in t for word in ["build", "code", "fix", "test", "focus", "deploy"]):
        return "focus"
    elif any(word in t for word in ["bro", "fam", "man", "lol", "haha", "wild", "crazy"]):
        return "cheeky"

    # 10–15% chance to go cheeky for style
    if random.random() < 0.15:
        return "cheeky"
    return "calm"

    
        

# -------------------------------------------------------------------------------------------
# Routes
# -------------------------------------------------------------------------------------------
# 3️⃣ Safe tone detection (only if text and function exist)
tone = None
try:
    if 'text' in locals():
        tone = detect_emotion_and_tone(text)
except Exception as e:
    print(f"[Tone Detection Error Ignored] {e}")




        
        
@app.get("/")
def home():
    try:
        return render_template("index.html")
    except Exception:
        return "SoNo server is running."

@app.get("/ask")
def ask_get_hint():
    return jsonify({"ok": True, "hint": "POST JSON to /ask with {\"text\": \"...\", \"profile\": \"ty|pam\"}"}), 200


@app.post("/mem/import")
def mem_import():
    data = request.get_json(silent=True) or {}
    mem = data.get("memory")
    if not isinstance(mem, dict):
        return jsonify({"ok": False, "error": "Provide JSON {\"memory\": {...}}"}), 400
    try:
        for sub, rels in mem.items():
            if not isinstance(rels, dict): continue
            for rel, val in rels.items():
                mem_remember(sub, rel, str(val))
        return jsonify({"ok": True, "imported": sum(len(v) for v in mem.values())})
    except Exception as e:
        return jsonify({"ok": False, "error": f"Import failed: {e}"}), 500

@app.get("/healthz")
def healthz():
    return jsonify({"ok": True, "status": "up"})

# Quick regression checks
GOLDEN_CASES: List[Tuple[str, str]] = [
    ("who are you", "identity"),
    ("what's your purpose", "identity"),
    ("my comfort snack is oranges", "teach"),
    ("what's my snack", "memory"),
    ("Pam’s comfort show is Sanford and Son", "teach"),
    ("what's her comfort show", "memory"),
    ("tell me something about pam", "memory"),
    ("actually hometown is los angeles", "teach"),
    ("what's her hometown", "memory"),
]
@app.get("/tests/smoke")
def tests_smoke():
    results = []
    for q, expected in GOLDEN_CASES:
        r = handle_question(q, profile="ty")
        results.append({"q": q, "got": r.get("source"), "ok": (r.get("source")==expected)})
    passed = sum(1 for r in results if r["ok"])
    return jsonify({"ok": True, "passed": passed, "total": len(results), "results": results})

@app.route("/mem/remember", methods=["POST"])
def mem_remember():
    """Add or update a memory fact."""
    try:
        data = request.get_json(force=True)
        subject = data.get("subject", "").strip()
        relation = data.get("relation", "").strip()
        value = data.get("value", "").strip()

        if not all([subject, relation, value]):
            return jsonify({"ok": False, "error": "Missing subject, relation, or value"}), 400

        # Clean phrasing
        for field in ["subject", "relation", "value"]:
            if isinstance(data.get(field), str):
                data[field] = (
                    data[field]
                    .strip()
                    .lower()
                    .replace("that ", "")
                    .replace(" is ", " ")
                    .replace(" my ", " ")
                    .replace("’", "'")
                    .replace("’s", "'s")
                )

        subject = data.get("subject")
        relation = data.get("relation")
        value = data.get("value")

        # --- detect duplicate before saving ---
        existing = memory.memory.get(subject, {}).get(relation, [])
        is_duplicate = value.lower() in [str(v).lower() for v in existing]

        memory.remember(subject, relation, value)

        if is_duplicate:
            msg = f"⚠️ Duplicate ignored: {subject} → {relation}: {value}"
        else:
            msg = f"✅ Remembered {subject} → {relation}: {value}"

        return jsonify({"ok": True, "message": msg})
    except Exception as e:
        print(f"[MEM ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


    
        # --------------------------------------------------------
# Emotion + Natural Response Layer
# --------------------------------------------------------

# quick emotion keyword map
EMOTION_RESPONSES = {
    "happy": "That’s good energy, Ty. Keep that momentum — that’s when breakthroughs show up.",
    "tired": "You’ve been grinding hard, Ty. Take a breath before you burn out — progress still counts when you rest.",
    "angry": "I hear the frustration, Ty. Let’s channel it into building, not burning out.",
    "sad": "That one hits deep. Remember you’re building a future that honors your past.",
    "focused": "Locked in, I like it. Let’s execute step by step.",
    "motivated": "Stay on that wave — this is where you start separating from the pack.",
    "miss": "I know that feeling hits deep. You’ve been carrying your loved ones through every build and every move you make."
}


# --------------------------------------------------------
# ---------- AUTO INTENT + PERSONALITY + PERSISTENCE ----------
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(silent=True)
        text = data.get("text", "").strip()
        answer = None  # ✅ initialize early to avoid 'unbound variable'

        if not text:
            return jsonify({"ok": False, "error": "Missing text"}), 400

        # ----- INTENT DETECTION -----
        lower = text.lower()
        intent = None
        subj, rel, val = None, None, None

        # --- INTENT PARSING ---
        intent = None

        # 🔹 REMEMBER intent
        if lower.startswith("remember"):
            intent = "remember"
            # Handle flexible grammar: is / are / was / were
            body = lower.replace("remember", "", 1).strip()
            parts = re.split(r"\b(is|are|was|were)\b", body, maxsplit=1)
            if len(parts) >= 3:
                left = parts[0].replace("that", "").replace("my", "").strip()
                val = parts[2].strip()
                subj = "ty"
                rel = left
                print(f"[ASK ROUTE] Entered remember branch: subj={subj}, rel={rel}, val={val}")

        # 🔹 RECALL intent (handles natural variants)
        elif any(lower.startswith(p) for p in [
            "what is", "whats", "what’s", "what was",
            "who is", "who are", "who’s", "who was",
            "tell me", "do you know", "what are"
        ]):
            intent = "recall"
            body = re.sub(r"^(what( is|’s|s)?|who( is|’s|s| are)?|tell me|do you know|what are)", "", lower).strip()
            rel = body.replace("my", "").replace("the", "").strip()
            subj = "ty"

            # Map common words like "kids" to consistent relations
            if rel in ["kids", "children", "sons", "daughters"]:
                rel = "kids"
            print(f"[ASK ROUTE] Entered recall branch: subj={subj}, rel={rel}")


        # 🔹 Fallback
        else:
            intent = "general"
            
                        # 🧠 Fuzzy recall logic
            from difflib import SequenceMatcher

            possible = list(memory.facts.keys())
            rels = [r for (s, r) in possible if s == subj]

            best_match = None
            best_ratio = 0.0
            for r in rels:
                ratio = SequenceMatcher(None, rel, r).ratio()
                if ratio > best_ratio:
                    best_match = r
                    best_ratio = ratio

            if best_match and best_ratio > 0.5:
                answer = memory.get(subj, best_match)
                print(f"[ASK ROUTE] ✅ Recall matched: {best_match} (ratio {best_ratio:.2f})")
            else:
                answer = None
                print(f"[ASK ROUTE] ⚠️ No strong match for '{rel}' (best={best_match}, ratio={best_ratio:.2f})")




        # ----- REMEMBER -----
        if intent == "remember" and subj and rel and val:
            memory.remember(subj, rel, val)
            memory._safe_write_json(memory.runtime_path, memory.memory)
            return jsonify({"ok": True, "answer": f"Got it. I’ll remember your {rel} is {val}."})

        # ----- RECALL -----
        if intent == "recall":
            answer = memory.search(text)
            if answer:
                return jsonify({"ok": True, "answer": answer})

        # ----- GPT FALLBACK -----
        if not answer and _openai_client:
            print("[Memory] No local recall found — escalating to GPT.")
            completion = _openai_client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": "You are SoulNode, Ty Butler’s AI co-pilot. Respond briefly and conversationally."},
                    {"role": "user", "content": text},
                ],
            )
            gpt_answer = completion.choices[0].message.content.strip()
            return jsonify({"ok": True, "answer": gpt_answer})

        # ----- FINAL FALLBACK -----
        return jsonify({
            "ok": False,
            "answer": "Try saying: 'Remember my dream car is ___' or 'What is my dream car?'"
        })

    except Exception as e:
        print(f"[app] /ask error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500



    
# -------------------------------
#  Voice / TTS (11Labs)
# -------------------------------
# ---- ElevenLabs Voice Setup ----
from flask import Response
import os

@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json(silent=True)
    text = (data.get("text") or data.get("prompt") or "").strip()

    # Detect emotional tone from the text
    tone = detect_emotion_and_tone(text)
    print(f"[TTS] Detected emotion: {tone}")

    if not text:
        return jsonify({"ok": False, "error": "Missing text"}), 400

    try:
        api_key = os.getenv("ELEVENLABS_API_KEY")

        if NEW_SDK:
            client = ElevenLabs(api_key=api_key)
            audio = client.text_to_speech.convert(
                voice_id="Rachel",
                model_id="eleven_multilingual_v2",
                text=text
            )
        else:
            audio = generate(text=text, voice="Rachel", api_key=api_key)

        return Response(audio, mimetype="audio/mpeg")

    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    
@app.route("/mem/sanitize", methods=["POST"])
def mem_sanitize():
    """Run a full sanitization sweep on all memory data."""
    try:
        memory.sanitize_all()
        return jsonify({"ok": True, "message": "Memory sweep completed successfully."})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    
# --------------------------------------------------------
# Memory Diagnostics & Export Endpoints
# --------------------------------------------------------

@app.route("/mem/status", methods=["GET"])
def mem_status():
    """Return memory diagnostics and current stats."""
    try:
        total_subjects = len(memory.memory)
        total_facts = sum(len(v) for v in memory.memory.values())
        last_sweep = getattr(memory, "last_sweep", "N/A")
        write_count = getattr(memory, "write_count", "N/A")

        return jsonify({
            "ok": True,
            "summary": {
                "subjects": total_subjects,
                "facts": total_facts,
                "write_count": write_count,
                "last_sweep": last_sweep
            }
        })
    except Exception as e:
        print(f"[MEM STATUS ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/mem/export", methods=["GET"])
def mem_export():
    """Export current memory as a downloadable JSON file."""
    try:
        if not os.path.exists(memory.runtime_path):
            return jsonify({"ok": False, "error": "Memory file not found"}), 404

        return send_file(
            memory.runtime_path,
            as_attachment=True,
            download_name="memory_store_backup.json",
            mimetype="application/json"
        )
    except Exception as e:
        print(f"[MEM EXPORT ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    

    
@app.route("/admin/mode", methods=["GET"])
def get_mode():
    """Check current operating mode."""
    return jsonify({"ok": True, "mode": MODE})



# --------------------------------------------------------
# Closed Test Activity Tracking
# --------------------------------------------------------


@app.route("/feedback", methods=["POST"])
@track_activity("feedback")
def feedback():
    """Record feedback from closed testers."""
    try:
        data = request.get_json(force=True)
        tester = data.get("tester", "unknown")
        message = data.get("message", "")
        rating = data.get("rating", "N/A")

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {"tester": tester, "message": message, "rating": rating, "timestamp": ts}

        # --- WRITE TO DISK ---
        log_path = os.path.join(os.path.dirname(__file__), "feedback_log.json")

        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)

        print(f"[Feedback] ✅ Logged from {tester} at {ts}")
        return jsonify({"ok": True, "message": "Feedback recorded."})
    except Exception as e:
        print(f"[FEEDBACK ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/tester/feedback", methods=["POST"])
@track_activity("tester_feedback")
def tester_feedback():
    """Allow registered testers to post feedback."""
    try:
        data = request.get_json(force=True)
        key = data.get("key", "").strip()
        message = data.get("message", "")
        rating = data.get("rating", "N/A")

        # --- LOAD REGISTRY ---
        reg_path = "tester_registry.json"
        if not os.path.exists(reg_path):
            return jsonify({"ok": False, "error": "Tester registry not found"}), 404
        
        # --- LOAD REGISTRY ---
        reg_path = "tester_registry.json"
        if not os.path.exists(reg_path):
            return jsonify({"ok": False, "error": "Tester registry not found"}), 404

        with open(reg_path, "r", encoding="utf-8") as f:
            testers = json.load(f)

        # Handle both dict and list formats
        tester_name = None
        if isinstance(testers, dict):
            tester_name = testers.get(key)
        elif isinstance(testers, list):
            for t in testers:
                if t.get("key", "").upper() == key.upper():
                    tester_name = t.get("name")
                    break


        with open(reg_path, "r", encoding="utf-8") as f:
            testers = json.load(f)

        tester_name = testers.get(key, None)
        if not tester_name:
            return jsonify({"ok": False, "error": "Invalid tester key"}), 401

        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {"tester": tester_name, "message": message, "rating": rating, "timestamp": ts}

        # --- WRITE TO LOG ---
        log_path = "feedback_log.json"
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(entry)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)

        print(f"[Tester Feedback] ✅ Logged from {tester_name} at {ts}")
        return jsonify({"ok": True, "message": f"Feedback recorded from {tester_name}."})
    except Exception as e:
        print(f"[TESTER FEEDBACK ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

    
# --------------------------------------------------------
# Closed Test Access & Tester Registry
# --------------------------------------------------------
import json, os
from datetime import datetime

TESTER_LOG_PATH = os.path.join("data", "tester_logs.json")
MAX_TESTERS = 5
ADMIN_KEY = "TYADMIN"

# Utility: load tester data
def load_testers():
    if os.path.exists(TESTER_LOG_PATH):
        with open(TESTER_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"testers": {}, "logs": []}

# Utility: save tester data
def save_testers(data):
    os.makedirs(os.path.dirname(TESTER_LOG_PATH), exist_ok=True)
    with open(TESTER_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

# --------------------------------------------------------
# Admin Command: Register Tester
# --------------------------------------------------------
@app.route("/tester/register", methods=["POST"])
def register_tester():
    try:
        data = request.get_json(force=True)
        admin_key = data.get("admin_key")
        name = data.get("name")
        key = data.get("key")

        if admin_key != ADMIN_KEY:
            return jsonify({"ok": False, "error": "Unauthorized"}), 403

        testers = load_testers()
        if len(testers["testers"]) >= MAX_TESTERS:
            return jsonify({"ok": False, "error": "Tester limit reached"}), 400

        testers["testers"][key] = {"name": name, "joined": datetime.now().isoformat()}
        save_testers(testers)
        return jsonify({"ok": True, "message": f"Tester '{name}' registered with key {key}."})
    except Exception as e:
        print(f"[TESTER REGISTER ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# --------------------------------------------------------
# Tester Feedback Submission
# --------------------------------------------------------
@app.route("/tester/submit", methods=["POST"])
def tester_submit():
    try:
        data = request.get_json(force=True)
        key = data.get("key")
        message = data.get("message")
        rating = data.get("rating")

        testers = load_testers()
        tester_info = testers["testers"].get(key)
        if not tester_info:
            return jsonify({"ok": False, "error": "Invalid tester key"}), 403

        log_entry = {
            "tester": tester_info["name"],
            "key": key,
            "message": message,
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }
        testers["logs"].append(log_entry)
        save_testers(testers)

        return jsonify({"ok": True, "message": "Tester feedback logged successfully."})
    except Exception as e:
        print(f"[TESTER SUBMIT ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# --------------------------------------------------------
# Admin Command: View Tester Logs
# --------------------------------------------------------
@app.route("/tester/logs", methods=["GET"])
def tester_logs():
    try:
        admin_key = request.args.get("admin_key")
        if admin_key != ADMIN_KEY:
            return jsonify({"ok": False, "error": "Unauthorized"}), 403

        testers = load_testers()
        return jsonify({"ok": True, "logs": testers["logs"], "testers": testers["testers"]})
    except Exception as e:
        print(f"[TESTER LOGS ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    
    # --------------------------------------------------------
# Closed Test Status Endpoint
# --------------------------------------------------------
# --------------------------------------------------------
# Admin: Closed Test Status Overview
# --------------------------------------------------------
# --------------------------------------------------------
# Admin: Closed Test Status Overview (Fixed JSON Formatting)
# --------------------------------------------------------
@app.route("/admin/test_status", methods=["GET"])
def admin_test_status():
    """Return summary of all feedback entries and tester activity (clean JSON)."""
    try:
        feedback_log = []
        if os.path.exists("feedback_log.json"):
            with open("feedback_log.json", "r", encoding="utf-8") as f:
                feedback_log = json.load(f)

        total_feedback = len(feedback_log)
        testers = {}
        latest_entry = None

        if feedback_log:
            latest_entry = feedback_log[-1]
            for entry in feedback_log:
                name = entry.get("tester", "Unknown")
                testers[name] = testers.get(name, 0) + 1

        summary_data = {
            "total_testers": len(testers),
            "total_feedback": total_feedback,
            "tester_activity": testers,
            "latest_entry": latest_entry
        }

        response = jsonify({
            "ok": True,
            "summary": summary_data
        })
        response.headers["Content-Type"] = "application/json"
        return response

    except Exception as e:
        print(f"[ADMIN TEST STATUS ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    
# --------------------------------------------------------
# Admin Dashboard View (Feedback Visualizer)
# --------------------------------------------------------
@app.route("/admin/dashboard", methods=["GET"])
def admin_dashboard():
    """Simple HTML dashboard to view feedback logs and tester stats."""
    feedback_path = Path("feedback_log.json")
    if not feedback_path.exists():
        return "<h2>No feedback data yet.</h2>"

    # Load feedback log
    with open(feedback_path, "r", encoding="utf-8") as f:
        logs = json.load(f)

    # Build table
    rows = ""
    for entry in reversed(logs):  # newest first
        rows += f"""
        <tr>
            <td>{entry.get('tester')}</td>
            <td>{entry.get('message')}</td>
            <td>{entry.get('rating')}</td>
            <td>{entry.get('timestamp')}</td>
        </tr>
        """

    html = f"""
    <html>
    <head>
        <title>SoulNode Closed Test Dashboard</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f9fafc;
                margin: 40px;
            }}
            h1 {{
                color: #222;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                background: white;
                border-radius: 8px;
                box-shadow: 0 0 8px rgba(0,0,0,0.1);
            }}
            th, td {{
                padding: 10px;
                border-bottom: 1px solid #ddd;
                text-align: left;
            }}
            th {{
                background: #0078d7;
                color: white;
            }}
            tr:hover {{
                background: #f1f1f1;
            }}
        </style>
    </head>
    <body>
        <h1>🧠 SoulNode Closed Test Dashboard</h1>
        <table>
            <tr>
                <th>Tester</th>
                <th>Message</th>
                <th>Rating</th>
                <th>Timestamp</th>
            </tr>
            {rows}
        </table>
    </body>
    </html>
    """
    return html


# --------------------------------------------------------
# Speech-to-Text Endpoint (Browser Mic → Text)
# --------------------------------------------------------
@app.route("/speech", methods=["POST"])
def speech_to_text():
    """
    Accepts an uploaded audio file and returns transcribed text.
    For now it just returns a dummy string until Whisper/other API wired in.
    """
    try:
        if "audio" not in request.files:
            return jsonify({"ok": False, "error": "No audio file uploaded"}), 400

        file = request.files["audio"]
        # Here you could hook in Whisper API or another STT service.
        # For now we just fake a response so testers can see it work:
        dummy_text = "This is a placeholder transcription from " + file.filename

        return jsonify({"ok": True, "text": dummy_text})
    except Exception as e:
        print(f"[SPEECH ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500




    

# --------------------------------------------------------
# Flask Entry Point
# --------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)


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

import os, re, json, time
from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
from difflib import SequenceMatcher
from collections import deque, Counter
from memory_store import MemoryStore
from flask import Flask, request, jsonify


from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template, make_response, Response

memory = MemoryStore()


# ---------------- SoulNode Identity Preload ----------------
try:
    memory.remember("solnode", "name", "SoulNode")
    memory.remember("solnode", "creator", "Ty Butler")
    memory.remember("solnode", "mission", "To learn, heal, and help build New Chapter Media’s legacy.")
    memory.remember("solnode", "origin", "New Chapter Media Group")
    memory.remember("solnode", "type", "AI co-pilot")
    print("[Identity] ✅ SoulNode identity preloaded into memory")
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_openai_client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        _openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print("OpenAI init error:", e)

# ---- Local modules (with safe fallbacks for utils) ----
from memory_store import MemoryStore
try:
    from ingest_pam import load_pam_facts as _load_pam_txt
except Exception:
    _load_pam_txt = None

try:
    from utils import save_memory as _save_memory, log_unknown_input as _log_unknown_input
except Exception:
    def _save_memory(*_a, **_k): pass
    def _log_unknown_input(*_a, **_k): pass

# -------------------------------------------------------------------------------------------
# App / Paths
# -------------------------------------------------------------------------------------------
app = Flask(__name__, template_folder="templates")

DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True, parents=True)

MEM_FILE = Path("memory_store.json")
SESSION_FILE = Path("session_memory.json") # if you use it, we won't choke
PAM_JSON = DATA_DIR / "pam_facts_flat.json"
PAM_TXT = DATA_DIR / "pam_facts_flat.json" if (DATA_DIR / "pam_facts_flat.json").exists() else Path("pam_facts_flat.json")

# Initialize MemoryStore with both pam facts and runtime memory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STORE = MemoryStore(
    base_dir=BASE_DIR,
    facts_file=str(PAM_JSON),
    runtime_file=str(MEM_FILE),
)

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


        
        # Detect emotional tone first — safe even if undefined
tone = None
try:
    tone = detect_emotion_and_tone(text)
except Exception as e:
    print(f"[Tone Detection Error] {e}")
    tone = None




@app.get("/")
def home():
    try:
        return render_template("index.html")
    except Exception:
        return "SoNo server is running."

@app.get("/ask")
def ask_get_hint():
    return jsonify({"ok": True, "hint": "POST JSON to /ask with {\"text\": \"...\", \"profile\": \"ty|pam\"}"}), 200

@app.get("/mem/export")
def mem_export():
    try:
        payload = store.export() if hasattr(store, "export") else {}
    except Exception:
        payload = {}
    sample = {
        "pam": {
            "full name": mem_recall("pam","full name"),
            "birthplace": mem_recall("pam","birthplace"),
            "hometown": mem_recall("pam","hometown"),
            "comfort show": mem_recall("pam","comfort show"),
            "comfort snack":mem_recall("pam","comfort snack"),
            "doctor": mem_recall("pam","doctor"),
            "phone": mem_recall("pam","phone"),
        },
        "ty": {
            "favorite color": mem_recall("ty","favorite color"),
            "hometown": mem_recall("ty","hometown"),
            "comfort snack": mem_recall("ty","comfort snack"),
            "doctor": mem_recall("ty","doctor"),
            "phone": mem_recall("ty","phone"),
        }
    }
    return jsonify({"ok": True, "memory": payload, "sample": sample})

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

@app.route("/remember", methods=["POST"])
def remember():
    """Safely save a new fact without causing reloader recursion."""
    try:
        data = request.get_json(force=True)
        subj = str(data.get("subject", "")).strip().lower()
        rel  = str(data.get("relation", "")).strip().lower()
        val  = str(data.get("value", "")).strip()

        if not subj or not rel or not val:
            return jsonify({"ok": False, "error": "Missing subject, relation, or value"}), 400

        # Make sure runtime memory exists
        if not hasattr(STORE, "memory"):
            STORE.memory = {}

        STORE.memory.setdefault(subj, {}).setdefault(rel, [])

        # Add only if not already stored
        if val not in STORE.memory[subj][rel]:
            STORE.memory[subj][rel].append(val)
            STORE._safe_write_json(STORE.runtime_path, STORE.memory)
            print(f"[Memory] ✅ Remembered clean fact: {subj} → {rel}: {val}")
        else:
            print(f"[Memory] ⚠️ Duplicate skipped: {subj} → {rel}")

        return jsonify({"ok": True, "saved": {"subject": subj, "relation": rel, "value": val}})

    except Exception as e:
        print(f"[Memory] ERROR in /remember: {e}")
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
# /ask route with emotion layer integrated
# --------------------------------------------------------
@app.route("/ask", methods=["POST"])
def ask():
    try:
        data = request.get_json(silent=True)
        text = data.get("text", "").strip().lower()

        if not text:
            return jsonify({"ok": False, "error": "Missing text"}), 400

        # --- 1️⃣ Auto-Intent: detect if user is giving a fact to remember ---
        remember_triggers = ["my ", "i weigh", "i am", "today is", "birthday", "favorite", "goal", "car", "color", "born", "name"]
        auto_intent = any(trigger in text for trigger in remember_triggers) and "?" not in text

        if "remember" in text or auto_intent:
            # extract a simple subject + relation + value
            subject = "ty"
            relation, value = None, None

            if "car" in text:
                relation = "dream car"
                value = text.split("car")[-1].strip().replace("is", "").strip()
            elif "color" in text:
                relation = "favorite color"
                value = text.split("color")[-1].strip().replace("is", "").strip()
            elif "goal" in text:
                relation = "goal"
                value = text.split("goal")[-1].strip().replace("is", "").strip()

            if relation and value:
                memory.remember(subject, relation, value)
                return jsonify({"ok": True, "answer": f"Got it. I’ll remember your {relation} is {value}."})

        # --- 2️⃣ Regular question lookup ---
        answer = memory.search(text)
        if not answer:
            answer = "(no answer found in memory)"
        print(f"[app] Q: {text} → A: {answer}")

        # --- 3️⃣ Tone detection ---
        tone = None
        try:
            if "?" not in text:
                if any(word in text for word in ["haha", "funny", "lol"]):
                    tone = "cheeky"
                elif any(word in text for word in ["focus", "locked", "discipline"]):
                    tone = "focus"
                elif any(word in text for word in ["legacy", "kids", "generational"]):
                    tone = "legacy"
                elif any(word in text for word in ["tired", "frustrated", "reflect"]):
                    tone = "reflective"
                elif any(word in text for word in ["let's go", "keep pushing", "rise", "grind"]):
                    tone = "motivational"
        except Exception as e:
            print(f"[Tone Detection Error] {e}")

        # --- 4️⃣ Add tone personality if found ---
        if tone and "(no answer found" not in str(answer).lower():
            tone_map = {
                "cheeky": "😏 Haha, you thought I’d forget that?",
                "focus": "🎯 Let’s keep it tight, zero distractions.",
                "legacy": "🏁 This one’s legacy talk — keep building for the ones watching.",
                "reflective": "💭 Take a breath. You’ve already won half the battle showing up.",
                "motivational": "🔥 Stay locked in, Commander — this is how we rise."
            }
            answer = f"{answer} {tone_map.get(tone, '')}"

        # --- 5️⃣ Return final response ---
        return jsonify({"ok": True, "answer": answer}), 200

    except Exception as e:
        print(f"[app] /ask error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500





   
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

        memory.remember(subject, relation, value)
        return jsonify({"ok": True, "message": f"Remembered {subject} → {relation}: {value}"})
    except Exception as e:
        print(f"[MEM ERROR] {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    
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

    # 10-15% chance to switch to cheeky randomly for spice
    if random.random() < 0.15:
        return "cheeky"
    return "calm"



# -------------------------------
#  Voice / TTS (11Labs)
# -------------------------------
# ---- ElevenLabs Voice Setup ----
from flask import Response
import os

@app.route("/tts", methods=["POST"])
def tts():
    data = request.get_json(silent=True)
    text = data.get("text", "").strip()

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


# -------------------------------------------------------------------------------------------
# Main
# -------------------------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)

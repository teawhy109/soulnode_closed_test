from __future__ import annotations

import io
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, request

# --------------------------------------------------------------------------------------------------
# Minimal "openai" shim so tests can monkeypatch ChatCompletion.create(...)
# (the tests do NOT actually call OpenAI; they patch this method to return a fake)
# --------------------------------------------------------------------------------------------------
class _ChatCompletionShim:
    @staticmethod
    def create(**kwargs):
        # If a test forgets to patch, fail loudly so we notice.
        raise RuntimeError("openai shim: tests will monkeypatch ChatCompletion.create")

class _OpenAIShim:
    ChatCompletion = _ChatCompletionShim

openai = _OpenAIShim() # module-level symbol that tests reference as appmod.openai

# --------------------------------------------------------------------------------------------------
# Flask app
# --------------------------------------------------------------------------------------------------
app = Flask(__name__)

# --------------------------------------------------------------------------------------------------
# Storage (project root files so tests can monkeypatch these paths)
# --------------------------------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent
_MEM_FILE: Path = _ROOT / "memory.json"
_BM_FILE: Path = _ROOT / "bookmarks.json"
_MOM_BM_FILE: Path = _ROOT / "mom_bookmarks.json"

# --------------------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------------------
def _utc_iso() -> str:
    # Keep semantics similar to earlier runs; tests only read strings
    return datetime.utcnow().isoformat()

def _read_json_list(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _write_json_list(path: Path, items: List[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

def _normalize_bookmarks(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    norm: List[Dict[str, Any]] = []
    for it in items:
        if isinstance(it, dict):
            norm.append({
                "bookmark": it.get("bookmark") or it.get("name") or "",
                "content": it.get("content") or "",
                "timestamp": it.get("timestamp") or "",
            })
    return norm

# Stubbed functions that tests monkeypatch in some blocks
def transcribe_audio(file_obj: io.BytesIO | Any) -> str:
    raise RuntimeError("tests will monkeypatch transcribe_audio")

def get_response_for_prompt(prompt: str) -> str:
    return prompt

def speak_text(text: str) -> None:
    return None

# --------------------------------------------------------------------------------------------------
# Block 01: root smoke
# --------------------------------------------------------------------------------------------------
@app.get("/")
def root():
    # Exact text expected by test_block_01_smoke.py
    return "SoulNode is active. Ready to receive your input.", 200

# --------------------------------------------------------------------------------------------------
# Block 02: process_audio
# --------------------------------------------------------------------------------------------------
@app.post("/process_audio")
def process_audio():
    f = request.files.get("audio") or request.files.get("file")
    if not f:
        return jsonify({"error": "audio file required"}), 400

    text = transcribe_audio(f) # tests monkeypatch
    # tests monkeypatch this openai call to return a fake response object
    resp = openai.ChatCompletion.create(
        model="none",
        messages=[{"role": "user", "content": text}],
    )
    answer = resp.choices[0].message["content"]
    try:
        speak_text(answer) # tests monkeypatch (no-op)
    except Exception:
        pass
    return jsonify({"response": answer}), 200

# --------------------------------------------------------------------------------------------------
# Block 04: (implemented in separate module audio_to_text_pipeline.py) — nothing here

# --------------------------------------------------------------------------------------------------
# Block 06: mode API
# --------------------------------------------------------------------------------------------------
_MODE = "soul"
_VALID = {"soul", "no_bullshit"}
_NORMALIZE = {"nobs": "no_bullshit", "no-bs": "no_bullshit", "nobullshit": "no_bullshit"}

@app.get("/mode")
def get_mode():
    return jsonify({"mode": _MODE}), 200

@app.post("/mode")
def set_mode():
    data = request.get_json(force=True) or {}
    raw = (data.get("mode") or "").strip().lower()
    mode = _NORMALIZE.get(raw, raw)
    if mode not in _VALID:
        return jsonify({"error": "invalid mode"}), 400
    global _MODE
    _MODE = mode
    return jsonify({"mode": _MODE}), 200

# --------------------------------------------------------------------------------------------------
# Block 08: process_text
# --------------------------------------------------------------------------------------------------
@app.post("/process_text")
def process_text():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or data.get("prompt") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400

    resp = openai.ChatCompletion.create(
        model="none",
        messages=[{"role": "user", "content": text}],
    )
    answer = resp.choices[0].message["content"]
    try:
        speak_text(answer)
    except Exception:
        pass
    return jsonify({"response": answer}), 200

# --------------------------------------------------------------------------------------------------
# Block 10: save memory + bookmark add
# --------------------------------------------------------------------------------------------------
@app.post("/save")
def save_memory():
    data = request.get_json(force=True) or {}
    content = (data.get("content") or "").strip()
    mem_type = (data.get("type") or "private").strip()
    if not content:
        return jsonify({"error": "content required"}), 400

    items = _read_json_list(_MEM_FILE)

    # internal id as integer (epoch ms)
    mem_id_int = int(datetime.utcnow().timestamp() * 1000)

    items.append({
        "id": mem_id_int, # keep int in storage
        "content": content,
        "type": mem_type,
    })
    _write_json_list(_MEM_FILE, items)

    # return id as STRING to satisfy tests
    return jsonify({
        "status": "ok",
        "data": {"id": str(mem_id_int), "content": content}
    }), 200

@app.post("/bookmark")
def bookmark_add():
    data = request.get_json(force=True) or {}
    name = (data.get("bookmark") or data.get("name") or "").strip()
    content = (data.get("content") or "").strip()
    if not name:
        return jsonify({"error": "bookmark required"}), 400

    items = _read_json_list(_BM_FILE)
    items.append({"bookmark": name, "content": content, "timestamp": _utc_iso()})
    _write_json_list(_BM_FILE, items)
    return jsonify({"status": "ok", "data": {"bookmark": name}}), 200

# --------------------------------------------------------------------------------------------------
# Block 11 & 13: status (+ counters)
# --------------------------------------------------------------------------------------------------
@app.get("/status")
def status():
    mems = _read_json_list(_MEM_FILE)
    bms = _read_json_list(_BM_FILE)
    return jsonify({
        "ok": True,
        "mode": _MODE,
        "counters": {"memories": len(mems), "bookmarks": len(bms)},
    }), 200

# --------------------------------------------------------------------------------------------------
# Block 12: escalation (simple keyword check)
# --------------------------------------------------------------------------------------------------
@app.post("/escalate")
def escalate():
    data = request.get_json(force=True) or {}
    msg = (data.get("message") or "").lower()
    if "emergency" in msg or "override" in msg:
        return jsonify({"response": "Escalation acknowledged", "level": "high"}), 200
    return jsonify({"status": "ok", "level": "none"}), 200

# --------------------------------------------------------------------------------------------------
# Block 14: memory search
# --------------------------------------------------------------------------------------------------
@app.get("/memory/search")
def memory_search():
    q = (request.args.get("query") or "").lower().strip()
    items = _read_json_list(_MEM_FILE)
    hits: List[Dict[str, Any]] = []
    if q:
        for it in items:
            if isinstance(it, dict):
                content = (it.get("content") or "").lower()
                if q in content:
                    hits.append(it)
    return jsonify(hits), 200

# --------------------------------------------------------------------------------------------------
# Block 16: memory list
# --------------------------------------------------------------------------------------------------
@app.get("/memory/list")
def memory_list():
    items = _read_json_list(_MEM_FILE)
    norm = [{"id": it.get("id"), "content": it.get("content", ""), "timestamp": it.get("timestamp", "")}
            for it in items if isinstance(it, dict)]
    return jsonify({"items": norm, "count": len(norm)}), 200

# --------------------------------------------------------------------------------------------------
# Block 17: memory delete by id
# --------------------------------------------------------------------------------------------------
@app.post("/memory/delete")
def memory_delete():
    data = request.get_json(force=True) or {}
    target_id = str(data.get("id") or "").strip()
    if not target_id:
        return jsonify({"error": "id required"}), 400
    items = _read_json_list(_MEM_FILE)
    new_items = [it for it in items if not (isinstance(it, dict) and str(it.get("id")) == target_id)]
    deleted = len(items) - len(new_items)
    _write_json_list(_MEM_FILE, new_items)
    return jsonify({"ok": True, "deleted": deleted, "id": target_id}), 200

# --------------------------------------------------------------------------------------------------
# Block 18: memory update by id
# --------------------------------------------------------------------------------------------------
@app.post("/memory/update")
def memory_update():
    data = request.get_json(force=True) or {}
    id_str = (str(data.get("id")) if data.get("id") is not None else "").strip()
    new_content = (data.get("content") or "").strip()
    if not id_str or not new_content:
        return jsonify({"error": "id and content required"}), 400

    try:
        id_int = int(id_str)
    except ValueError:
        return jsonify({"error": "invalid id"}), 400

    items = _read_json_list(_MEM_FILE)
    updated = False
    for it in items:
        if isinstance(it, dict) and it.get("id") == id_int:
            it["content"] = new_content
            updated = True
            break
    _write_json_list(_MEM_FILE, items)

    if not updated:
        return jsonify({"ok": False, "id": id_str}), 404

    # IMPORTANT: return id as STRING (tests do int(body["id"]) == mem_id)
    return jsonify({"ok": True, "id": id_str}), 200
# --------------------------------------------------------------------------------------------------
# Block 19: bookmark list
# --------------------------------------------------------------------------------------------------
@app.get("/bookmark/list")
def bookmark_list():
    items = _read_json_list(_BM_FILE)
    norm = _normalize_bookmarks(items)
    return jsonify({"items": norm, "count": len(norm)}), 200

# --------------------------------------------------------------------------------------------------
# Block 20: bookmark delete by name
# --------------------------------------------------------------------------------------------------
@app.post("/bookmark/delete")
def bookmark_delete():
    data = request.get_json(force=True) or {}
    name = (data.get("name") or data.get("bookmark") or "").strip()
    if not name:
        return jsonify({"error": "bookmark name required"}), 400
    items = _read_json_list(_BM_FILE)
    new_items = [it for it in items if not (isinstance(it, dict) and (it.get("bookmark") or "") == name)]
    deleted = len(items) - len(new_items)
    _write_json_list(_BM_FILE, new_items)
    # Return a normalized list like other endpoints (tests read names & count)
    norm_after = _normalize_bookmarks(new_items)
    return jsonify({"status": "ok", "deleted": deleted, "items": norm_after, "count": len(norm_after)}), 200

# --------------------------------------------------------------------------------------------------
# Block 21: bookmark search (substring on name/content)
# --------------------------------------------------------------------------------------------------
@app.get("/bookmark/search")
def bookmark_search():
    q = (request.args.get("q") or request.args.get("query") or "").lower().strip()
    items = _read_json_list(_BM_FILE)
    hits: List[Dict[str, Any]] = []
    if q:
        for it in items:
            if isinstance(it, dict):
                name = (it.get("bookmark") or "").lower()
                content = (it.get("content") or "").lower()
                if q in name or q in content:
                    hits.append({"bookmark": it.get("bookmark", ""), "content": it.get("content", "")})
    return jsonify(hits), 200

# --------------------------------------------------------------------------------------------------
# Block 22: mom-scoped bookmarks (separate file)
# --------------------------------------------------------------------------------------------------
@app.post("/mom/bookmark/add")
def mom_bookmark_add():
    data = request.get_json(force=True) or {}
    name = (data.get("bookmark") or data.get("name") or "").strip()
    content = (data.get("content") or "").strip()
    if not name:
        return jsonify({"error": "bookmark required"}), 400
    items = _read_json_list(_MOM_BM_FILE)
    items.append({"bookmark": name, "content": content, "timestamp": _utc_iso()})
    _write_json_list(_MOM_BM_FILE, items)
    return jsonify({"status": "ok"}), 200

@app.get("/mom/bookmark/list")
def mom_bookmark_list():
    items = _read_json_list(_MOM_BM_FILE)
    norm = _normalize_bookmarks(items)
    return jsonify({"items": norm, "count": len(norm)}), 200

# --------------------------------------------------------------------------------------------------
# Main (manual run)
# --------------------------------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
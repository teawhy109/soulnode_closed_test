from pathlib import Path
import json
from typing import List, Dict, Any

# Returns a list of dicts like {"content": "..."} for the given user_id.
# It looks for common files you already have; falls back to an empty list.
def get_all_memories(user_id: str) -> List[Dict[str, Any]]:
    candidates = [
        Path("memory/memory_log.json"),
        Path("memory/memories.json"),
        Path("SessionMemory.json"),
        Path("core_memory.json"), # will be filtered safely
        Path("backup_memory.json"),
    ]

    entries: List[Dict[str, Any]] = []
    for p in candidates:
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue

        # Normalize various shapes to [{"content": "...", "user_id": "..."}]
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    content = (
                        item.get("content")
                        or item.get("value") # e.g., core_memory.json style
                        or ""
                    )
                    uid = item.get("user_id") or item.get("user") or "unknown"
                    if content:
                        entries.append({"content": content, "user_id": uid})
        elif isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
            for item in data["items"]:
                if isinstance(item, dict):
                    content = item.get("content", "")
                    uid = item.get("user_id") or "unknown"
                    if content:
                        entries.append({"content": content, "user_id": uid})

    # If the file(s) didn’t carry user ids, don’t over-filter; otherwise filter by user_id
    has_user_ids = any(e.get("user_id") not in (None, "unknown") for e in entries)
    if has_user_ids:
        entries = [e for e in entries if e.get("user_id") == user_id]

    # Only return the shape the app endpoint expects
    return [{"content": e.get("content", "")} for e in entries if e.get("content")]
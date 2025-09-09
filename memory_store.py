# memory_store.py (drop-in replacement)
from __future__ import annotations
from threading import RLock
import json, os, tempfile
from typing import Dict, Any

class MemoryStore:
    """
    Simple persistent key-value graph:
      {
        "ty": { "mom": "pam", "coffee order": "cortado" },
        "ivy": { "favorite color": "royal blue" }
      }
    - Keys (subject, relation) are normalized to lowercase + trimmed.
    - File is auto-created and auto-healed if corrupted/wrong type.
    - All writes are atomic to avoid corruption.
    """

    def __init__(self, path: str = "./data/memory.json"):
        self.path = path
        self.lock = RLock()
        self.mem: Dict[str, Dict[str, Any]] = {}
        self._init_dirs()
        self._load()

    # ---------- Private helpers ----------

    def _init_dirs(self) -> None:
        # Ensure parent directory exists (e.g., ./data/)
        parent = os.path.dirname(self.path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)

    def _atomic_write(self) -> None:
        # Write self.mem to disk safely
        parent = os.path.dirname(self.path) or "."
        fd, tmp = tempfile.mkstemp(dir=parent, prefix="mem_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.mem, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except Exception:
            # Best effort cleanup if replace fails
            try:
                os.remove(tmp)
            except Exception:
                pass
            raise

    def _load(self) -> None:
        # Load file; if corrupted or wrong type, reset to {}
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}

            if isinstance(data, dict):
                # Ensure nested values are dicts/strings only
                safe: Dict[str, Dict[str, Any]] = {}
                for subj, kv in data.items():
                    if not isinstance(subj, str) or not isinstance(kv, dict):
                        continue
                    subj_key = self._norm(subj)
                    safe[subj_key] = {}
                    for rel, val in kv.items():
                        if not isinstance(rel, str):
                            continue
                        rel_key = self._norm(rel)
                        # Store primitives as-is; stringify other types
                        safe[subj_key][rel_key] = val if isinstance(val, (str, int, float, bool)) else str(val)
                self.mem = safe
            else:
                self.mem = {}
                self._atomic_write()
        else:
            self.mem = {}
            self._atomic_write()

    @staticmethod
    def _norm(s: str) -> str:
        return (s or "").strip().lower()

    # ---------- Public API ----------

    def remember(self, subject: str, relation: str, value: Any) -> None:
        """Create/overwrite a fact."""
        with self.lock:
            subject_k = self._norm(subject)
            relation_k = self._norm(relation)
            if subject_k == "" or relation_k == "":
                return
            bucket = self.mem.setdefault(subject_k, {})
            bucket[relation_k] = value
            self._atomic_write()

    def recall(self, subject: str, relation: str) -> Any | None:
        """Read a fact (or None)."""
        subject_k = self._norm(subject)
        relation_k = self._norm(relation)
        return self.mem.get(subject_k, {}).get(relation_k)

    def update(self, subject: str, relation: str, value: Any) -> None:
        """Alias of remember; keeps API clear."""
        self.remember(subject, relation, value)

    def forget(self, subject: str, relation: str) -> bool:
        """Delete a fact. Returns True if something was deleted."""
        with self.lock:
            subject_k = self._norm(subject)
            relation_k = self._norm(relation)
            bucket = self.mem.get(subject_k)
            if not bucket or relation_k not in bucket:
                return False
            del bucket[relation_k]
            if not bucket:
                del self.mem[subject_k]
            self._atomic_write()
            return True

    def clear_all(self) -> None:
        """Dangerous: wipe everything."""
        with self.lock:
            self.mem = {}
            self._atomic_write()

    def export_all(self) -> Dict[str, Dict[str, Any]]:
        """Return an in-memory snapshot (do not mutate the result directly)."""
        return self.mem

    def import_all(self, data: Dict[str, Dict[str, Any]]) -> None:
        """Replace DB with provided dict (keys normalized)."""
        if not isinstance(data, dict):
            return
        with self.lock:
            fresh: Dict[str, Dict[str, Any]] = {}
            for subj, kv in data.items():
                if not isinstance(subj, str) or not isinstance(kv, dict):
                    continue
                subj_k = self._norm(subj)
                fresh[subj_k] = {}
                for rel, val in kv.items():
                    if not isinstance(rel, str):
                        continue
                    rel_k = self._norm(rel)
                    fresh[subj_k][rel_k] = val if isinstance(val, (str, int, float, bool)) else str(val)
            self.mem = fresh
            self._atomic_write()
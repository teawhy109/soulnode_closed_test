# soulnode_memory.py
from __future__ import annotations
import os, json, threading
from typing import List, Dict, Optional

class SoulNodeMemory:
    def __init__(self, owner_name: str = "Ty", store_path: str = "data/memory.json"):
        self.owner = owner_name
        self.store_path = store_path
        self._lock = threading.Lock()
        self._facts: List[Dict[str, str]] = []
        os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
        self._load()

    def remember(self, subj: str, rel: str, obj: str) -> str:
        with self._lock:
            self._facts.append({"subj": subj.strip(), "rel": rel.strip(), "obj": obj.strip()})
            self._save()
        return f"Saved: {subj} {rel} {obj}"

    def lookup(self, subj: str, rel: str) -> Optional[str]:
        s = subj.strip().lower()
        r = rel.strip().lower()
        with self._lock:
            for fact in reversed(self._facts):
                if fact["subj"].strip().lower() == s and fact["rel"].strip().lower() == r:
                    return fact["obj"]
        return None

    def export(self) -> List[Dict[str, str]]:
        with self._lock:
            return list(self._facts)

    def _load(self) -> None:
        if os.path.exists(self.store_path):
            try:
                with open(self.store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self._facts = data
            except Exception:
                self._facts = []

    def _save(self) -> None:
        try:
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(self._facts, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
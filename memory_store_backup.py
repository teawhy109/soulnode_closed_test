# ============================================================
# memory_store.py  —  Stable Full Version (Fixed October 2025)
# ============================================================

import json
import os
import re
from typing import Optional, Tuple, Dict, Any, List

STORE_PATH = os.path.join(os.path.dirname(__file__), "memory_store.json")

NAME_RX = r"[A-Za-z][A-Za-z\-']+"
REL_RX = r"[A-Za-z][A-Za-z\- ]+"

INVERSE = {
    "husband": "wife",
    "wife": "husband",
    "mother": "child",
    "father": "child",
    "son": "parent",
    "daughter": "parent",
}

class MemoryStore:
    def __init__(self, base_dir=None, facts_file=None, runtime_file=None):
        import os
        self.base_dir = base_dir or os.getcwd()
        self.facts_path = facts_file or os.path.join(self.base_dir, "data", "pam_facts_fixed.json")
        self.runtime_path = runtime_file or os.path.join(self.base_dir, "memory_store.json")
        self.facts = {}
        self.memory = {}

        # Load both static and runtime memory at initialization
        self._load_static_facts()
        self._load_runtime_memory()
        
    def _load_static_facts(self):
        """Load static data (like Pam's facts) from JSON."""
        try:
            import json
            if not os.path.exists(self.facts_path):
                print(f"[Memory] No static facts file found at {self.facts_path}")
                return

            with open(self.facts_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            for subj, rels in data.items():
                subj_l = subj.strip().lower()
                self.facts.setdefault(subj_l, {})
                for rel, vals in rels.items():
                    rel_l = rel.replace("_", " ").strip().lower()
                    if isinstance(vals, list):
                        self.facts[subj_l][rel_l] = vals
                    else:
                        self.facts[subj_l][rel_l] = [vals]

            print(f"[Memory] Loaded {len(data)} subject(s) from {self.facts_path}")
        except Exception as e:
            print(f"[Memory] Error loading facts: {e}")
            
    def _load_runtime_memory(self):
        """Load dynamic (runtime) memory from JSON file."""
        try:
            import json
            if not os.path.exists(self.runtime_path):
                print(f"[Memory] No runtime file found at {self.runtime_path}")
                return

            with open(self.runtime_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                print("[Memory] Runtime memory file not in expected dict format.")
                data = {}

            self.memory = data
            print(f"[Memory] Runtime memory loaded ({len(self.memory)} subjects)")

        except Exception as e:
            print(f"[Memory] Error loading runtime memory: {e}")
            self.memory = {}
       



    # ------------------------------------------------------------
    # Safe JSON utilities
    # ------------------------------------------------------------
    def _safe_read_json(self, path: str) -> Any:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Memory] JSON read error from {path}: {e}")
            return {}

    def _safe_write_json(self, path: str, data: Any):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[Memory] Saved {len(data)} items → {path}")
        except Exception as e:
            print(f"[Memory] JSON write error to {path}: {e}")

    # ------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------

            

    # ------------------------------------------------------------
    # Save runtime memory
    # ------------------------------------------------------------
    def _save_runtime(self):
        self._safe_write_json(self.runtime_path, self.memory)

    # ------------------------------------------------------------
    # Remember / Forget
    # ------------------------------------------------------------
    def remember(self, subject: str, relation: str, value: str):
        """Store fact cleanly, preventing nested lists or duplicates."""
        s, r, v = subject.strip().lower(), relation.strip().lower(), str(value).strip()

        # Initialize subject & relation
        self.memory.setdefault(s, {}).setdefault(r, [])

        # Only store unique, non-empty values
        if v and v not in self.memory[s][r]:
            self.memory[s][r].append(v)
            self._safe_write_json(self.runtime_path, self.memory)
            print(f"[Memory] ✅ Remembered clean fact: {s} → {r}: {v}")
        else:
            print(f"[Memory] (skip duplicate) {s} → {r}: {v}")
 


    def forget(self, subject: str, relation: Optional[str] = None):
        """Forget a subject or a specific relation."""
        s = subject.strip().lower()
        if s not in self.memory:
            return
        if relation:
            r = relation.strip().lower()
            if r in self.memory[s]:
                del self.memory[s][r]
                print(f"[Memory] Forgot relation {r} for {s}")
        else:
            del self.memory[s]
            print(f"[Memory] Forgot subject {s}")
        self._save_runtime()

    # ------------------------------------------------------------
    # Search / Recall
    # ------------------------------------------------------------
    from difflib import SequenceMatcher
    import re

    def search(self, query: str) -> Optional[str]:
        """Search both facts and runtime memory for an answer (smart recall)."""
        if not query:
            return None
        q = query.lower().strip()

        subj_map = {"my mom": "pam", "mom": "pam", "you": "ty", "ty": "ty", "pam": "pam"}
        q = q.replace("’", "'").replace("?", "")

        subj, rel = None, None

        m = re.search(r"(?:what|who)\s+is\s+(?P<subj>my mom|mom|you|ty|pam|[a-zA-Z]+)'?s?\s+(?P<rel>.+)", q)
        if m:
            subj = subj_map.get(m.group("subj"), m.group("subj"))
            rel = m.group("rel").strip()

        if not subj:
            parts = q.split()
            if parts:
                subj = subj_map.get(parts[0], parts[0])
                rel = " ".join(parts[1:])

        if subj and rel:
            if subj in self.memory and rel in self.memory[subj]:
                vals = self.memory[subj][rel]
                return ", ".join(vals)
            if subj in self.facts and rel in self.facts[subj]:
                vals = self.facts[subj][rel]
                return ", ".join(vals)

        words = re.findall(r"[a-z']+", q)
        if subj:
            for r, vals in {**self.memory.get(subj, {}), **self.facts.get(subj, {})}.items():
                score = SequenceMatcher(None, r, " ".join(words)).ratio()
                if score > 0.7:
                    return ", ".join(vals)

        return None


    
    def recall(self, subject: str, relation: str) -> Optional[str]:
        """Retrieve a fact from runtime or static memory."""
        s = subject.strip().lower()
        r = relation.replace("_", " ").strip().lower()

        # Check runtime memory first
        if s in self.memory and r in self.memory[s]:
           return ", ".join(self.memory[s][r])

        # Then check static facts
        if s in self.facts and r in self.facts[s]:
           return ", ".join(self.facts[s][r])

        # Try inverse lookup (e.g., "Who is Rickey’s wife" → "Pam")
        inv = INVERSE.get(r)
        if inv:
           combined = {**self.facts, **self.memory}
        for sub, rels in combined.items():
            if inv in rels and s in [v.lower() for v in rels[inv]]:
                return sub.capitalize()

        return None


        # ------------------------------------------------------------
    # Query Parsing (Fixed version)
    # ------------------------------------------------------------
    def _parse_query(self, q: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract subject and relation from a query string, normalizing underscores and spacing."""
        q = q.replace("’", "'").replace("?", "").strip().lower()

        # Normalize punctuation and possessives
        m = re.search(r"who\s+is\s+(" + NAME_RX + r")'?s?\s+(" + REL_RX + r")", q)
        if m:
            subj, rel = m.groups()
        else:
            m = re.search(r"what\s+is\s+(" + NAME_RX + r")'?s?\s+(" + REL_RX + r")", q)
            if m:
                subj, rel = m.groups()
            else:
                parts = q.split()
                if len(parts) >= 2:
                    subj, rel = parts[0], parts[1]
                else:
                    return None, None

        # Normalize subject & relation
        subj = subj.strip().lower()
        rel = rel.strip().lower().replace("_", " ")

        # Handle special patterns like birthplace → birth place
        rel = (
            rel.replace("birthplace", "birth place")
            .replace("fullname", "full name")
            .replace("nicknamebyfamily", "nickname by family")
            .replace("nicknamebygrandkids", "nickname by grandkids")
        )

        return subj, rel


    # ------------------------------------------------------------
    # Aliases and Helpers
    # ------------------------------------------------------------
    def alias_subject(self, subj: str) -> str:
        """Resolve common nicknames or alternate spellings."""
        aliases = {
            "pam": "pamela",
            "ricky": "rickey",
            "ty": "tyease",
            "aja": "aja",
            "jade": "jade"
        }
        s = subj.lower().strip()
        return aliases.get(s, s)

    # ------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------
    def export_memory(self, path: Optional[str] = None):
        """Export combined memory (facts + runtime) to file."""
        out_path = path or "memory_export.json"
        data = {
            "facts": self.facts,
            "runtime": self.memory
        }
        self._safe_write_json(out_path, data)
        print(f"[Memory] Exported all memory → {out_path}")

    def import_memory(self, path: str):
        """Import external memory data."""
        data = self._safe_read_json(path)
        if not isinstance(data, dict):
            print("[Memory] Invalid import file")
            return
        facts = data.get("facts", {})
        runtime = data.get("runtime", {})
        if isinstance(facts, dict):
            self.facts.update(facts)
        if isinstance(runtime, dict):
            self.memory.update(runtime)
        self._save_runtime()
        print(f"[Memory] Imported memory from {path}")

    # ------------------------------------------------------------
    # Reset / Clear
    # ------------------------------------------------------------
    def clear_all(self):
        """Completely clear runtime memory (use with caution)."""
        self.memory = {}
        self._save_runtime()
        print("[Memory] All runtime memory cleared")

    def clear_subject(self, subject: str):
        """Clear a specific subject from both memories."""
        s = subject.lower().strip()
        removed = False
        if s in self.memory:
            del self.memory[s]
            removed = True
        if s in self.facts:
            del self.facts[s]
            removed = True
        if removed:
            self._save_runtime()
            print(f"[Memory] Cleared subject '{s}'")
        else:
            print(f"[Memory] Subject '{s}' not found")

    # ------------------------------------------------------------
    # Diagnostics / Debugging
    # ------------------------------------------------------------
    def summary(self):
        """Print a concise summary of memory state."""
        print("========== MEMORY SUMMARY ==========")
        print(f"Static facts subjects : {len(self.facts)}")
        print(f"Runtime memory subjects: {len(self.memory)}")
        print("====================================")

    def list_subjects(self):
        """List all known subjects."""
        subs = sorted(set(list(self.facts.keys()) + list(self.memory.keys())))
        print(f"Subjects ({len(subs)}): {', '.join(subs)}")

    # ------------------------------------------------------------
    # Stand-alone Test Harness
    # ------------------------------------------------------------
if __name__ == "__main__":
    print("Running standalone memory store test...\n")
    mem = MemoryStore()

    mem.summary()
    mem.list_subjects()

    print("\n--- Sample Queries ---")
    tests = [
        "What is Pam's full name?",
        "Who is Pam's husband?",
        "Who are Pam's children?",
        "What is Pam's birthplace?"
    ]
    for q in tests:
        ans = mem.search(q)
        print(f"Q: {q}")
        print(f"A: {ans}\n")

    print("--- Remembering New Facts ---")
    mem.remember("Ty", "goal", "Build SoulNode legacy system")
    mem.remember("Ty", "vehicle_goal", "Cadillac Escalade ESV V")

    print("\n--- Exporting Memory Snapshot ---")
    mem.export_memory("memory_export_test.json")

    print("\n--- Clearing and Re-Loading ---")
    mem.clear_all()
    mem.import_memory("memory_export_test.json")
    mem.summary()
    print("\n[Memory Test Completed]")

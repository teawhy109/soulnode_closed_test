import json
import os
import re
from typing import Optional, Tuple, Any
from difflib import SequenceMatcher


# ---------- constants ----------
# Use Render's persistent /data directory if available
STORE_PATH = os.path.join("/data", "memory_store.json")


if not os.path.exists(STORE_PATH):
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump({}, f)



# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------
STORE_PATH = os.path.join(os.path.dirname(__file__), "memory_store.json")
FACTS_PATH = os.path.join(os.path.dirname(__file__), "data", "pam_facts_fixed.json")

INVERSE = {
    "husband": "wife",
    "wife": "husband",
    "mother": "child",
    "father": "child",
    "son": "parent",
    "daughter": "parent",
}

NAME_RX = r"[A-Za-z\-']+"
REL_RX = r"[A-Za-z][A-Za-z\- ]+"

# ------------------------------------------------------------
# MemoryStore Class
# ------------------------------------------------------------
class MemoryStore:
    def __init__(self, base_dir: str = ".", facts_file: str = None, runtime_file: str = "memory_store.json"):
        """Initialize memory store with optional paths."""
        self.base_dir = base_dir
        self.facts_file = facts_file
        self.runtime_path = runtime_file
        self.memory = {}
        self.facts = {}

        # 🧠 Auto-clean tracking
        self.write_count = 0  # Track how many times memory was saved
        self.last_sweep = None  # Track the last time the auto-clean ran

        # Load static facts if file exists
        if self.facts_file and os.path.exists(self.facts_file):
            try:
                with open(self.facts_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # make sure it's a dict
                    if isinstance(data, dict):
                        self.facts = data
                        print(f"[Memory] Loaded {len(self.facts)} subject(s) from {self.facts_file}")
                    else:
                        print(f"[Memory] Warning: facts file is not a dict ({type(data)})")
            except Exception as e:
                print(f"[Memory] Error loading facts: {e}")

        # Load runtime memory
        if os.path.exists(self.runtime_path):
            try:
                with open(self.runtime_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.memory = data
                        print(f"[Memory] Runtime memory loaded ({len(self.memory)} subjects)")
            except Exception as e:
                print(f"[Memory] Error loading runtime memory: {e}")
                
    def _safe_write_json(self, path, data):
        """Safely write data to JSON file."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"[Memory] Saved {len(data)} items → {path}")
        except Exception as e:
            print(f"[Memory] Error writing {path}: {e}")
            
    # --------------------------------------------------------
    # Deduplicate Helper
    # --------------------------------------------------------
    def _dedupe(self, values):
        """Flatten deeply nested memory values and remove duplicates cleanly."""
        flat = []

        def flatten(item):
            if isinstance(item, list):
                for i in item:
                    flatten(i)
            elif isinstance(item, str):
                # Clean out weird nested quote layers
                cleaned = item.strip(" []'\"")
                if cleaned:
                    flat.append(cleaned)

        flatten(values)

        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for val in flat:
            if val not in seen:
                seen.add(val)
                unique.append(val)
        return unique


    # --------------------------------------------------------
    # Remember
    # --------------------------------------------------------
    def remember(self, subject: str, relation: str, value, silent: bool = False):
        """Store a (subject, relation, value) triple, avoid duplicates, and sanitize values."""
        try:
            # Normalize the value
            if isinstance(value, list):
                flat = []
                for v in value:
                    if isinstance(v, list):
                        flat.extend(v)
                    else:
                        v = str(v).strip("[]'\" ")
                        if v and v not in flat:
                            flat.append(v)
                value = flat[0] if len(flat) == 1 else flat
            elif isinstance(value, str):
                value = value.strip("[]'\" ")

            # Prep keys
            subj_key = subject.lower().strip()
            rel_key = relation.lower().strip()

            # Initialize subject section if needed
            if subj_key not in self.memory:
                self.memory[subj_key] = {}

            # Retrieve and normalize existing values
            existing = self.memory[subj_key].get(rel_key, [])
            if not isinstance(existing, list):
                existing = [existing]

            # Prevent duplicates (deep clean version)
            existing_clean = [str(v).strip("[]'\" ").lower() for v in existing]
            value_clean = str(value).strip("[]'\" ").lower()

            if value_clean not in existing_clean:
                existing_clean.append(value_clean)
                self.memory[subj_key][rel_key] = existing_clean
                self.save()
                print(f"[Memory] ✅ Remembered: {subject} → {relation}: {value_clean}")
            else:
                print(f"[Memory] ⚠️ Duplicate ignored: {subject} → {relation}: {value_clean}")

        except Exception as e:
            print(f"[Memory Remember Error] {e}")







    # --------------------------------------------------------
    # Search / Recall
    # --------------------------------------------------------
    def search(self, query: str) -> Optional[str]:
        """Precision search — finds the best matching relation and avoids overlaps."""
        if not query:
            return None

        q = query.lower().strip()

        # subject aliases
        subj_alias = {
            "my": "ty",
            "me": "ty",
            "ty": "ty",
            "you": "ty",
            "i": "ty",
            "myself": "ty",
            "mom": "pam",
            "mother": "pam",
            "pamlea": "pam",
            "pam": "pam",
        }

        subj = "ty"
        for k, v in subj_alias.items():
            if f"{k} " in q or q.startswith(k):
                subj = v
                break

        # extract potential relation
        rel = None
        trigger_words = ["my ", "favorite ", "dream ", "goal ", "mission ", "type ", "name ", "color ", "movie "]
        for t in trigger_words:
            if t in q:
                parts = q.split(t, 1)
                if len(parts) > 1:
                    rel = parts[1].strip(" ?.")
                    break

        if subj not in self.memory and subj not in self.facts:
            return None

        all_data = {**self.memory.get(subj, {}), **self.facts.get(subj, {})}

        # 1️⃣ Exact match first
        if rel and rel in all_data:
            return ", ".join(all_data[rel])

        # 2️⃣ Partial match fallback
        for r, vals in all_data.items():
            if rel and rel in r:
                return ", ".join(vals)

        # 3️⃣ Fuzzy match backup
        from difflib import SequenceMatcher
        best_score, best_value = 0, None
        for r, vals in all_data.items():
            score = SequenceMatcher(None, q, r).ratio()
            if score > best_score:
                best_score, best_value = score, ", ".join(vals)
        if best_score > 0.6:
            return best_value

        return None




    # --------------------------------------------------------
    # Parse Query
    # --------------------------------------------------------
    def _parse_query(self, q: str) -> Tuple[Optional[str], Optional[str]]:
        """Extract subject and relation from natural queries like 'my mom's full name'."""
        q = q.lower().replace("?", "").replace("’", "'").strip()

        subj_map = {
            "my mom": "pam",
            "mom": "pam",
            "mother": "pam",
            "you": "ty",
            "your": "ty",
            "ty": "ty",
            "pam": "pam"
        }

        # look for patterns like "what is my mom's full name"
        m = re.search(r"(?:what|who)\s+(?:is|are)\s+(?:my\s+)?([a-z' ]+?)'s\s+([a-z ]+)", q)
        if m:
            subj, rel = m.groups()
            subj = subj_map.get(subj.strip(), subj.strip())
            return subj, rel.strip()

        # simpler "what is pam full name"
        m = re.search(r"(?:what|who)\s+(?:is|are)\s+([a-z' ]+)\s+([a-z ]+)", q)
        if m:
            subj, rel = m.groups()
            subj = subj_map.get(subj.strip(), subj.strip())
            return subj, rel.strip()

        # fallback — "my mom full name"
        parts = q.split()
        for key in subj_map:
            if key in q:
                subj = subj_map[key]
                rel = q.replace(key, "").replace("what", "").replace("is", "").replace("are", "").strip()
                return subj, rel
        return None, None
    
    def save(self):
        """Safely save current runtime memory to disk."""
        try:
            path = getattr(self, "runtime_path", None)
            if not path:
                path = STORE_PATH
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.memory, f, indent=2, ensure_ascii=False)

            # 🧹 Auto-clean trigger every 100 saves or every 24 hours
            import datetime
            self.write_count += 1
            now = datetime.datetime.now()

            if self.write_count >= 100 or (
                self.last_sweep and (now - self.last_sweep).total_seconds() >= 86400
            ):
                print("[Memory] 🧹 Auto-sweep triggered (threshold reached).")
                try:
                    self.sanitize_all()
                    self.last_sweep = now
                    self.write_count = 0
                    print("[Memory] ✅ Auto-sweep completed successfully.")
                except Exception as e:
                    print(f"[Memory] ⚠️ Auto-sweep failed: {e}")

            print(f"[Memory] Saved {len(self.memory)} items → {os.path.basename(path)}")

        except Exception as e:
            print(f"[Memory Save Error] {e}")



                # ---------- persistence layer ----------
    def load_persistent_memory(self):
        """Load memory from disk into runtime."""
        if not os.path.exists(STORE_PATH):
            return {}
        try:
            with open(STORE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[Memory] ⚠️ Failed to load persistent memory: {e}")
            return {}
        
            # --------------------------------------------------------
    # Memory Sanitization Sweep
    # --------------------------------------------------------
    def sanitize_all(self):
        """Cleans all stored memory entries by removing duplicates and nested junk."""
        try:
            clean_mem = {}
            for subject, facts in self.memory.items():
                clean_mem[subject] = {}
                for rel, vals in facts.items():
                    if not isinstance(vals, list):
                        vals = [vals]
                    clean = []
                    for v in vals:
                        if isinstance(v, str):
                            v = v.strip("[]'\" ").lower()
                        if v and v not in clean:
                            clean.append(v)
                    clean_mem[subject][rel] = clean
            self.memory = clean_mem
            self.save()
            print("[Memory Sweep] ✅ All memory entries sanitized and saved.")
        except Exception as e:
            print(f"[Memory Sweep Error] {e}")



    



# ------------------------------------------------------------
# Standalone Test
# ------------------------------------------------------------
if __name__ == "__main__":
    print("Running standalone memory store test...\n")
    store = MemoryStore()
    print(f"Subjects: {', '.join(store.memory.keys()) or '(none)'}")

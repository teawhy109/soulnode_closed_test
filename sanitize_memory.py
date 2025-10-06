import json
from pathlib import Path

# --- CONFIG ---
MEM_FILE = Path("memory_store.json")

def clean_value(val):
    """Strip brackets, quotes, and redundant nesting."""
    if isinstance(val, str):
        v = val.strip().strip("[]'\" ")
        if v.startswith("[") and v.endswith("]"):
            try:
                inner = json.loads(v.replace("'", '"'))
                if isinstance(inner, list):
                    return [clean_value(x) for x in inner]
                else:
                    return [str(inner)]
            except Exception:
                return [v]
        return [v]
    elif isinstance(val, list):
        flat = []
        for x in val:
            flat.extend(clean_value(x))
        return flat
    else:
        return [str(val)]

def sanitize_memory():
    if not MEM_FILE.exists():
        print(f"[❌] No file found at {MEM_FILE}")
        return

    with open(MEM_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cleaned = {}
    for subj, rels in data.items():
        cleaned[subj] = {}
        for rel, vals in rels.items():
            flat = []
            for v in vals:
                flat.extend(clean_value(v))
            # Deduplicate and clean again
            uniq = []
            for v in flat:
                v = v.strip()
                if v and v not in uniq:
                    uniq.append(v)
            cleaned[subj][rel] = uniq

    # Save cleaned data
    backup = MEM_FILE.with_suffix(".bak.json")
    MEM_FILE.rename(backup)
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, indent=2)
    print(f"[✅] Memory sanitized and saved.\n[💾] Backup created at: {backup}")

if __name__ == "__main__":
    sanitize_memory()

# ingest_pam.py — subject-aware, canonical relations, smart lists
import re, sys
from soulnode_memory import SoulNodeMemory

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def split_list(text: str):
    if not text: return []
    t = re.sub(r"\s+(?:and|&)\s+", ",", text, flags=re.I)
    parts = [clean(p) for p in t.split(",")]
    return [p for p in parts if p]

# Decide SUBJECT from the question text
def subject_from_q(q: str) -> str:
    ql = q.lower()
    if "rickey" in ql or "ricky" in ql or "rickey butler" in ql or "ricky butler" in ql:
        return "Rickey Butler"
    if "pamela" in ql or "pam " in ql or "pam's" in ql or "pam butler" in ql:
        return "Pam"
    # default to Pam
    return "Pam"

def to_triplets(q: str, a: str):
    Q = clean(q).lower()
    A = clean(a)
    subj = subject_from_q(Q)
    trips = []

    # Helpers
    def add(rel, obj):
        trips.append((subj, rel, obj))

    # ----- Canonical mappings -----
    if re.search(r"\bwhere\s+was\s+.*\bborn\b", Q):
        add("birthplace", A); return trips

    if re.search(r"\bwhen\s+(?:is|was)\s+.*\b(birthday|birthdate|date of birth|dob)\b", Q):
        add("birthday", A); return trips

    if re.search(r"\bwho\s+(?:primarily\s+)?raised\b", Q):
        add("raised by", split_list(A) or A); return trips

    if re.search(r"\b(husband|spouse)\b", Q):
        add("husband", A); return trips

    if re.search(r"\bsiblings?\b", Q):
        add("siblings", split_list(A) or A); return trips

    if re.search(r"\b(children|kids|sons?|daughters?)\b", Q):
        add("children", split_list(A) or A); return trips

    if re.search(r"\bfavorite\s+restaurants?\b", Q):
        add("favorite restaurants", split_list(A) or A); return trips

    if re.search(r"\bfavorite\s+(?:foods?|meals?)\b", Q):
        add("favorite foods", split_list(A) or A); return trips

    if re.search(r"\bschools?\s+did\s+.*\battend\b|\bwhere\s+.*\beducated\b", Q):
        add("schools attended", split_list(A) or A); return trips

    if re.search(r"\bfull\s+name\b", Q):
        add("full name", A); return trips

    if re.search(r"\b(singers|bands|music)\b", Q):
        add("music taste", A); return trips

    # Special composite Q from your file: "Where was Rickey born and educated?"
    if "where was rickey born and educated" in Q:
        # Example A looked like: "Born in Los Angeles, California; attended Manual Arts Junior High and graduated from Washington High School."
        # Try to split into two facts
        born = re.search(r"born in ([^;]+)", A, flags=re.I)
        sch = re.search(r"(?:attended|educated at)\s+(.+)$", A, flags=re.I)
        if born: add("birthplace", clean(born.group(1)))
        if sch: add("schools attended", split_list(sch.group(1)) or clean(sch.group(1)))
        if trips: return trips

    # Fallback: store under stripped question
    add(Q.rstrip("?."), A)
    return trips

def parse_file(path: str):
    out = []
    q, a = None, None
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("Q:"):
                if q and a: out.append((q, a))
                q, a = line[2:].strip(), None
            elif line.startswith("A:"):
                a = (line[2:].strip() if a is None else (a + " " + line[2:].strip()))
            else:
                if a is not None and line.strip():
                    a += " " + line.strip()
        if q and a: out.append((q, a))
    return out

def ingest(path: str, dry_run=True):
    mem = SoulNodeMemory()
    seen = set()
    for q, a in parse_file(path):
        for subj, rel, obj in to_triplets(q, a):
            key = (subj.lower(), rel.lower(), str(obj).lower())
            if key in seen: 
                continue
            seen.add(key)
            if dry_run:
                print(f"[DRY] {subj} | {rel} | {obj}")
            else:
                mem.save_fact(subj, rel, obj)
                print(f"[SAVE] {subj} | {rel} | {obj}")
    if not dry_run and hasattr(mem, "_save"):
        mem._save()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_pam.py data/pam.txt [--dry-run]")
        sys.exit(1)
    path = sys.argv[1]
    dry = ("--dry-run" in sys.argv)
    ingest(path, dry_run=dry)

    # ingest_pam.py
from typing import List, Tuple
import re

QA = List[Tuple[str, str]]

_q = re.compile(r"^\s*Q:\s*(.+)$", re.I)
_a = re.compile(r"^\s*A:\s*(.+)$", re.I)

STOP = {"the","a","an","is","are","was","were","to","of","in","for","on","at","and","do","did","does","you","your"}

def _norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _keywords(s: str):
    return {w for w in _norm(s).split() if w not in STOP}

def load_pam_pairs(path) -> QA:
    pairs: QA = []
    q = None
    for line in open(path, "r", encoding="utf-8"):
        mQ = _q.match(line)
        mA = _a.match(line)
        if mQ:
            q = mQ.group(1).strip()
            continue
        if mA and q:
            a = mA.group(1).strip()
            pairs.append((q, a))
            q = None
    return pairs

def qa_answer(user_text: str, pairs: QA) -> str | None:
    """Very simple matcher: find the Q whose keywords are mostly in the user text."""
    uks = _keywords(user_text)
    if not uks:
        return None
    best = (0.0, None) # (score, answer)
    for q, a in pairs:
        qks = _keywords(q)
        if not qks:
            continue
        hit = len(qks & uks)
        score = hit / len(qks)
        if score > best[0]:
            best = (score, a)
    # require a modest match
    return best[1] if best[0] >= 0.5 else None
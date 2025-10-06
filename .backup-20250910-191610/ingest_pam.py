# ingest_pam.py
# -----------------------------------------
# Utilities to ingest Q:/A: content from data/pam.txt
# and provide simple retrieval helpers.
#
# Exposed functions:
# - load_pam_pairs(path: Path) -> list[tuple[str, str]]
# - load_pam_facts(path: Path) -> dict[str, str]
# - qa_answer(user_question: str, facts: dict[str, str]) -> str | None
# - save_facts_json(facts: dict[str, str], out_path: Path) -> None
#
# No external deps; standard library only.

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple, Dict, Optional
import json
import re


# ---------- normalization ----------

_WHITESPACE = re.compile(r"\s+")
_PUNCT = re.compile(r"[^\w\s]") # remove punctuation for matching


def _basic_norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = _WHITESPACE.sub(" ", s)
    return s


def normalize_question(q: str) -> str:
    """
    Aggressive but safe normalization used for keys:
    - lowercase
    - strip punctuation
    - collapse whitespace
    """
    q = _basic_norm(q)
    q = _PUNCT.sub(" ", q)
    q = _WHITESPACE.sub(" ", q).strip()
    return q


# ---------- parsing pam.txt ----------

def load_pam_pairs(path: Path) -> List[Tuple[str, str]]:
    """
    Scan a pam.txt file and return list of (question, answer) pairs.
    Lines starting with 'Q:' denote a question; the next 'A:' line is its answer.
    Blank lines are ignored. Multiple paragraphs in answers are supported until
    the next 'Q:' appears.
    """
    pairs: List[Tuple[str, str]] = []

    q: Optional[str] = None
    a_buf: List[str] = []

    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")

            if not line.strip():
                # allow blank lines inside answers
                if a_buf:
                    a_buf.append("")
                continue

            lower = line.lstrip().lower()
            if lower.startswith("q:"):
                # flush previous pair
                if q is not None and a_buf:
                    a = "\n".join(a_buf).strip()
                    if a:
                        pairs.append((q.strip(), a))
                # start new question
                q = line.split(":", 1)[1].strip()
                a_buf = []
                continue

            if lower.startswith("a:"):
                # start/append answer content
                a_line = line.split(":", 1)[1].strip()
                a_buf.append(a_line)
                continue

            # continuation of answer paragraph if we already saw 'A:'
            if a_buf:
                a_buf.append(line)

    # flush tail
    if q is not None and a_buf:
        a = "\n".join(a_buf).strip()
        if a:
            pairs.append((q.strip(), a))

    return pairs


def load_pam_facts(path: Path) -> Dict[str, str]:
    """
    Return dict of {normalized_question: answer} from pam.txt.
    """
    facts: Dict[str, str] = {}
    for q, a in load_pam_pairs(path):
        key = normalize_question(q)
        # last one wins if duplicates
        facts[key] = a
    return facts


# ---------- retrieval ----------

def _tokenize(s: str) -> List[str]:
    return [t for t in normalize_question(s).split() if t]


def qa_answer(user_question: str, facts: Dict[str, str]) -> Optional[str]:
    """
    Try to find the best answer from facts for a free-form user question.
    Strategy (in order):
      1) exact key match (normalized)
      2) startswith match over keys
      3) highest token-overlap score over keys
    Returns None if nothing decent is found.
    """
    if not user_question:
        return None

    nq = normalize_question(user_question)

    # 1) exact
    if nq in facts:
        return facts[nq]

    # 2) startswith over keys
    for k, v in facts.items():
        if nq.startswith(k) or k.startswith(nq):
            return v

    # 3) token overlap
    uq = set(_tokenize(user_question))
    if not uq:
        return None

    best_key = None
    best_score = 0.0

    for k in facts.keys():
        kt = set(k.split())
        if not kt:
            continue
        inter = len(uq & kt)
        score = inter / float(len(uq))
        if score > best_score:
            best_score = score
            best_key = k

    # choose only if overlap is meaningful
    if best_key and best_score >= 0.4:
        return facts[best_key]

    return None


# ---------- optional export ----------

def save_facts_json(facts: Dict[str, str], out_path: Path) -> None:
    """
    Save facts to a JSON file for inspection or other tooling.
    Schema: [{"q": "<normalized q>", "a": "<answer>"}, ...]
    """
    payload = [{"q": k, "a": v} for k, v in facts.items()]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


# ---------- CLI helper (optional) ----------

if __name__ == "__main__":
    # Simple manual test:
    pam_path = Path("data/pam.txt")
    facts = load_pam_facts(pam_path)
    print(f"Ingested {len(facts)} facts from {pam_path}")

    # Example query loop
    try:
        while True:
            q = input("Ask> ").strip()
            if not q:
                continue
            if q.lower() in {"quit", "exit"}:
                break
            ans = qa_answer(q, facts)
            print(ans if ans else "(no match)")
    except KeyboardInterrupt:
        pass
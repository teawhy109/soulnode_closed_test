#!/usr/bin/env python3
import argparse
import json
import os
import re
from typing import Dict, List, Tuple, Set

def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())

def _canon_subject(s: str) -> str:
    s = (s or "").strip().lower()
    # collapse common aliases for Pam into "pam" without touching value text
    aliases = {
        "pam", "pamela", "pamlea", "mother", "mom",
        "ty's mom", "tys mom", "ty’s mom", "ty s mom"
    }
    return "pam" if s in aliases else s

def _canon_relation(r: str) -> str:
    r = (r or "").strip().lower()
    if not r:
        return "fact"
    # spaces/dashes to underscores; collapse duplicate underscores
    r = r.replace("-", " ").replace("/", " ").replace(".", " ")
    r = re.sub(r"[^a-z0-9\s_]", "", r)
    r = re.sub(r"\s+", "_", r)
    r = re.sub(r"_+", "_", r)
    return r.strip("_") or "fact"

def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def write_json(path: str, data) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

def backup(path: str) -> str:
    bak = path + ".bak"
    if not os.path.exists(bak):
        with open(path, "rb") as src, open(bak, "wb") as dst:
            dst.write(src.read())
    return bak

def as_flat_facts(data) -> Tuple[List[Dict], str]:
    """
    Returns (facts_list, shape), where shape is "flat" if {"facts":[...]} or "unknown".
    We stick with flat output regardless (your MemoryStore loader reads flat fine).
    """
    # Already flat?
    if isinstance(data, dict) and isinstance(data.get("facts"), list):
        return data["facts"], "flat"

    # Nested or unknown — attempt to flatten best-effort
    flat: List[Dict] = []
    if isinstance(data, dict):
        # Expect nested shape: { "pam": { "relation": [values] or value } }
        for subj, rels in data.items():
            if not isinstance(rels, dict):
                # If someone stored a raw list, bring it through as-is
                if isinstance(rels, list):
                    for v in rels:
                        flat.append({
                            "subject": _canon_subject(subj),
                            "relation": "fact",
                            "value": _norm_space(str(v)),
                        })
                continue
            for rel, vals in rels.items():
                if isinstance(vals, list):
                    for v in vals:
                        flat.append({
                            "subject": _canon_subject(subj),
                            "relation": _canon_relation(rel),
                            "value": _norm_space(str(v)),
                        })
                else:
                    flat.append({
                        "subject": _canon_subject(subj),
                        "relation": _canon_relation(rel),
                        "value": _norm_space(str(vals)),
                    })
        return flat, "nested"
    # Fallback: not a dict/list we recognize
    return [], "unknown"

def dedupe_and_normalize(facts: List[Dict]) -> List[Dict]:
    seen: Set[Tuple[str, str, str]] = set()
    out: List[Dict] = []
    for rec in facts:
        subject = _canon_subject(rec.get("subject", ""))
        relation = _canon_relation(rec.get("relation", ""))
        value = _norm_space(str(rec.get("value", "")))

        # preserve original_q if present
        out_rec = {"subject": subject, "relation": relation, "value": value}
        if "original_q" in rec and isinstance(rec["original_q"], str):
            oq = _norm_space(rec["original_q"])
            if oq:
                out_rec["original_q"] = oq

        key = (subject, relation, value.lower())
        if key in seen:
            continue
        seen.add(key)
        out.append(out_rec)
    return out

def main():
    ap = argparse.ArgumentParser(description="Remaster pam_facts_flat.json in-place without losing facts.")
    ap.add_argument("--in", dest="input_path", required=True, help="Path to input JSON (e.g., data/pam_facts_flat.json)")
    ap.add_argument("--out", dest="output_path", required=True, help="Path to output JSON (can be the same as --in)")
    args = ap.parse_args()

    if not os.path.exists(args.input_path):
        raise SystemExit(f"[remaster] Input file not found: {args.input_path}")

    data = load_json(args.input_path)
    facts_in, shape = as_flat_facts(data)

    before = len(facts_in)
    facts_out = dedupe_and_normalize(facts_in)
    after = len(facts_out)

    # Always write flat shape: {"facts": [...]}
    result = {"facts": facts_out}

    # Backup and write
    backup(args.output_path)
    write_json(args.output_path, result)

    # Summary
    # Count by relation (top 10) — quick visibility
    rel_counts: Dict[str, int] = {}
    for r in facts_out:
        rel_counts[r["relation"]] = rel_counts.get(r["relation"], 0) + 1
    top = sorted(rel_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]

    print("[remaster] Done.")
    print(f"[remaster] Input shape: {shape}")
    print(f"[remaster] Facts before: {before}")
    print(f"[remaster] Facts after : {after} (removed {before - after} exact duplicates)")
    if top:
        print("[remaster] Top relation counts:")
        for rel, cnt in top:
            print(f" - {rel}: {cnt}")

if __name__ == "__main__":
    main()
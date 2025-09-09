# knowledgefeed.py — robust, back-compat knowledge ingestion
import os, csv, json
from pathlib import Path
from typing import Iterable, List, Dict, Any, Optional

try:
    import yaml # optional
except Exception:
    yaml = None

TRIPLE_SEP = "|"

class KnowledgeFeed:
    """
    Ingests fact triples from a folder of files into MEM (SoulNodeMemory-like API).
    Supported:
      - .txt lines: "Subject | relation | Object"
      - .txt blocks: subject:, relation:, object: (order-insensitive, blank-line separated)
      - .txt Q/A: Q: ... A: ... -> saves as: subject="Q", relation="A", object="<answer>"
      - .json: one of:
                        [{"subject":"...", "relation":"...", "object":"..."}, ...]
                        {"facts":[...triples...]}
                     (any other JSON shapes are skipped safely)
      - .jsonl: one triple per line as JSON object
      - .yaml/.yml: same shapes as .json (if PyYAML is available)
      - .csv: headers must include subject, relation, object (case-insensitive)
    On any error or unknown shape, the file is skipped instead of crashing the app.
    """

    def __init__(self, mem, root: Optional[str | Path] = "knowledge"):
        self.mem = mem
        self.root = Path(root) if root else Path("knowledge")
        self.stats = {"files": 0, "saved": 0, "skipped_files": 0, "skipped_rows": 0, "errors": []}

    # ---- Public API ---------------------------------------------------------
    def ingest_paths(self, targets: Optional[Iterable[str | Path]] = None) -> Dict[str, Any]:
        if not targets:
            targets = [self.root]
        for t in targets:
            self._ingest_target(Path(t))
        return {"ok": True, **self.stats}

    # Back-compat alias (your app.py may call this)
    def ingest_targets(self, targets: Optional[Iterable[str | Path]] = None) -> Dict[str, Any]:
        return self.ingest_paths(targets)

    # ---- Internals ----------------------------------------------------------
    def _ingest_target(self, p: Path):
        if not p.exists():
            self.stats["errors"].append(f"Missing target: {p}")
            self.stats["skipped_files"] += 1
            return
        if p.is_file():
            self._ingest_file(p)
        else:
            for f in p.rglob("*"):
                if f.is_file():
                    self._ingest_file(f)

    def _ingest_file(self, f: Path):
        ext = f.suffix.lower()
        try:
            if ext == ".txt":
                self._ingest_txt(f)
            elif ext == ".json":
                self._ingest_json(f)
            elif ext == ".jsonl":
                self._ingest_jsonl(f)
            elif ext in (".yaml", ".yml"):
                self._ingest_yaml(f)
            elif ext == ".csv":
                self._ingest_csv(f)
            else:
                # silently ignore non-knowledge files
                self.stats["skipped_files"] += 1
                return
            self.stats["files"] += 1
        except Exception as e:
            self.stats["errors"].append(f"{f.name}: {e}")
            self.stats["skipped_files"] += 1

    # ---- Parsers ------------------------------------------------------------
    def _save(self, subject: str, relation: str, obj: Any):
        ok, _ = self.mem.save_fact(subject, relation, obj)
        if ok:
            self.stats["saved"] += 1
        else:
            self.stats["skipped_rows"] += 1

    def _ingest_txt(self, f: Path):
        text = f.read_text(encoding="utf-8", errors="ignore")
        # 1) Triple lines: "A | rel | B"
        did_any = False
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            if TRIPLE_SEP in line and ("|" in line):
                parts = [p.strip() for p in line.split(TRIPLE_SEP)]
                if len(parts) >= 3 and all(parts[:2]) and parts[2] != "":
                    self._save(parts[0], parts[1], TRIPLE_SEP.join(parts[2:]).strip())
                    did_any = True

        # 2) subject:/relation:/object: block style
        block_sub, block_rel, block_obj = None, None, None
        for raw in text.splitlines() + [""]:
            line = raw.strip()
            if not line:
                if block_sub and block_rel and block_obj is not None:
                    self._save(block_sub, block_rel, block_obj)
                    did_any = True
                block_sub = block_rel = block_obj = None
                continue
            low = line.lower()
            if low.startswith("subject:"):
                block_sub = line.split(":", 1)[1].strip()
            elif low.startswith("relation:"):
                block_rel = line.split(":", 1)[1].strip()
            elif low.startswith("object:"):
                block_obj = line.split(":", 1)[1].strip()

        # 3) Q/A style
        q_curr = None
        for raw in text.splitlines() + [""]:
            line = raw.strip()
            if line.lower().startswith("q:"):
                q_curr = line[2:].strip()
            elif line.lower().startswith("a:") and q_curr:
                ans = line[2:].strip()
                self._save("Q", "A", f"{q_curr} -> {ans}")
                q_curr = None
                did_any = True

        if not did_any:
            # Not a knowledge .txt; ignore without error
            self.stats["skipped_files"] += 1

    def _ingest_json(self, f: Path):
        data = json.loads(f.read_text(encoding="utf-8", errors="ignore"))
        rows = None
        if isinstance(data, dict) and "facts" in data and isinstance(data["facts"], list):
            rows = data["facts"]
        elif isinstance(data, list):
            rows = data
        else:
            # not a mapping or list of mappings → skip safely
            self.stats["skipped_files"] += 1
            return
        for i, row in enumerate(rows):
            if not isinstance(row, dict):
                self.stats["skipped_rows"] += 1
                continue
            s = (row.get("subject") or "").strip()
            r = (row.get("relation") or "").strip()
            o = row.get("object")
            if s and r and o is not None:
                self._save(s, r, o)
            else:
                self.stats["skipped_rows"] += 1

    def _ingest_jsonl(self, f: Path):
        with f.open("r", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    self.stats["skipped_rows"] += 1
                    continue
                if not isinstance(row, dict):
                    self.stats["skipped_rows"] += 1
                    continue
                s = (row.get("subject") or "").strip()
                r = (row.get("relation") or "").strip()
                o = row.get("object")
                if s and r and o is not None:
                    self._save(s, r, o)
                else:
                    self.stats["skipped_rows"] += 1

    def _ingest_yaml(self, f: Path):
        if yaml is None:
            self.stats["errors"].append(f"{f.name}: pyyaml not installed")
            self.stats["skipped_files"] += 1
            return
        data = yaml.safe_load(f.read_text(encoding="utf-8", errors="ignore"))
        rows = None
        if isinstance(data, dict) and "facts" in data and isinstance(data["facts"], list):
            rows = data["facts"]
        elif isinstance(data, list):
            rows = data
        else:
            self.stats["skipped_files"] += 1
            return
        for row in rows:
            if not isinstance(row, dict):
                self.stats["skipped_rows"] += 1
                continue
            s = (row.get("subject") or "").strip()
            r = (row.get("relation") or "").strip()
            o = row.get("object")
            if s and r and o is not None:
                self._save(s, r, o)
            else:
                self.stats["skipped_rows"] += 1

    def _ingest_csv(self, f: Path):
        with f.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
            rdr = csv.DictReader(fh)
            # normalize headers
            field_map = {k.lower(): k for k in rdr.fieldnames or []}
            s_key = field_map.get("subject")
            r_key = field_map.get("relation")
            o_key = field_map.get("object")
            if not (s_key and r_key and o_key):
                self.stats["skipped_files"] += 1
                return
            for row in rdr:
                s = (row.get(s_key) or "").strip()
                r = (row.get(r_key) or "").strip()
                o = row.get(o_key)
                if s and r and o is not None:
                    self._save(s, r, o)
                else:
                    self.stats["skipped_rows"] += 1
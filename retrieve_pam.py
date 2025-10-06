# retriever_pam.py
# Simple semantic retriever for data/pam.txt (no extra libs; numpy only)

import os, re, json, pathlib, math
from typing import List, Tuple, Optional
import numpy as np
from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small" # cheap + good
CHUNKS_JSON = pathlib.Path("data/pam_chunks.json")
VECTORS_NPY = pathlib.Path("data/pam_vectors.npy")

def _split_paragraphs(text: str) -> List[str]:
    # split on blank lines; keep paragraphs short-ish
    parts = re.split(r"\n\s*\n", text.strip())
    chunks = []
    for p in parts:
        p = re.sub(r"\s+", " ", p.strip())
        if not p:
            continue
        # further split very long paragraphs
        if len(p) > 600:
            # split on sentences approx
            sentences = re.split(r"(?<=[\.\?\!])\s+", p)
            cur = []
            cur_len = 0
            for s in sentences:
                if cur_len + len(s) > 500 and cur:
                    chunks.append(" ".join(cur).strip())
                    cur, cur_len = [], 0
                cur.append(s)
                cur_len += len(s) + 1
            if cur:
                chunks.append(" ".join(cur).strip())
        else:
            chunks.append(p)
    return chunks

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = (np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0: return 0.0
    return float(np.dot(a, b) / denom)

def _load_text(path: pathlib.Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

def _need_rebuild(pam_txt: pathlib.Path) -> bool:
    if not CHUNKS_JSON.exists() or not VECTORS_NPY.exists():
        return True
    # if pam.txt is newer than index, rebuild
    return pam_txt.stat().st_mtime > min(CHUNKS_JSON.stat().st_mtime, VECTORS_NPY.stat().st_mtime)

class PamRetriever:
    def __init__(self, pam_txt_path: pathlib.Path):
        self.pam_txt_path = pam_txt_path
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.chunks: List[str] = []
        self.vectors: Optional[np.ndarray] = None

    def ensure_index(self):
        if _need_rebuild(self.pam_txt_path):
            self._build_index()
        else:
            try:
                self.chunks = json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))
                self.vectors = np.load(str(VECTORS_NPY))
            except Exception:
                self._build_index()
        return self

    def _build_index(self):
        text = _load_text(self.pam_txt_path)
        if not text:
            self.chunks, self.vectors = [], None
            return
        chunks = _split_paragraphs(text)
        # embed in small batches to avoid long prompts
        vecs = []
        B = 64
        for i in range(0, len(chunks), B):
            batch = chunks[i:i+B]
            resp = self.client.embeddings.create(
                model=EMBED_MODEL,
                input=batch
            )
            vecs.extend([np.array(d.embedding, dtype=np.float32) for d in resp.data])
        self.chunks = chunks
        self.vectors = np.stack(vecs, axis=0) if vecs else None
        CHUNKS_JSON.write_text(json.dumps(self.chunks, ensure_ascii=False, indent=2), encoding="utf-8")
        if self.vectors is not None:
            np.save(str(VECTORS_NPY), self.vectors)

    def search(self, query: str, k: int = 3, threshold: float = 0.72) -> List[Tuple[float, str]]:
        if not self.chunks or self.vectors is None:
            return []
        q = self.client.embeddings.create(model=EMBED_MODEL, input=[query]).data[0].embedding
        qv = np.array(q, dtype=np.float32)
        # cosine vs all
        sims = self.vectors @ qv / (np.linalg.norm(self.vectors, axis=1) * (np.linalg.norm(qv) + 1e-9) + 1e-9)
        idx = np.argsort(-sims)[:k]
        out = []
        for i in idx:
            score = float(sims[i])
            if score >= threshold:
                out.append((score, self.chunks[int(i)]))
        return out

    def answer(self, query: str) -> Optional[str]:
        # only try for PAM-ish queries to avoid hijacking general Qs
        t = (query or "").lower()
        if not any(w in t for w in ("pam", "ty's mom", "ty’s mom", "tys mom", "mom", "mother")):
            return None
        hits = self.search(query, k=3, threshold=0.70)
        if not hits:
            return None
        # light stitch of top hits
        paras = [p for _, p in hits]
        # keep it under ~500 chars
        out = []
        total = 0
        for p in paras:
            if total + len(p) > 500:
                break
            out.append(p)
            total += len(p)
        return " ".join(out).strip()

# simple module-level helpers
_PAM_RET: Optional[PamRetriever] = None

def init_pam_retriever(pam_txt_path: pathlib.Path) -> Optional[PamRetriever]:
    global _PAM_RET
    ret = PamRetriever(pam_txt_path).ensure_index()
    _PAM_RET = ret
    return ret

def retrieve_pam_answer(ret: Optional[PamRetriever], text: str) -> Optional[str]:
    if not ret:
        return None
    return ret.answer(text)
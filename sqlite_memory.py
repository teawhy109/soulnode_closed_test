import sqlite3
import json
import os
import math
from difflib import SequenceMatcher
from openai import OpenAI

# ------------------------------
# CONFIGURATION
# ------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "memory_store.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if OPENAI_API_KEY:
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("[SQLiteMemory] ✅ OpenAI client ready.")
    except Exception as e:
        print(f"[SQLiteMemory] ⚠️ OpenAI init failed: {e}")
else:
    print("[SQLiteMemory] ⚠️ No OPENAI_API_KEY detected; semantic recall disabled.")


# ------------------------------
# DATABASE INITIALIZATION
# ------------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS facts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            relation TEXT NOT NULL,
            value TEXT NOT NULL,
            embedding TEXT,
            UNIQUE(subject, relation, value)
        )
    """)
    conn.commit()
    conn.close()
    print("[SQLiteMemory] ✅ Database initialized.")
init_db()


# ------------------------------
# CORE CLASS
# ------------------------------
class SQLiteMemory:
    def __init__(self):
        self.db_path = DB_PATH

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _embed(self, text: str):
        if not client or not text:
            return None
        try:
            resp = client.embeddings.create(model=EMBED_MODEL, input=text)
            return json.dumps(resp.data[0].embedding)
        except Exception as e:
            print(f"[Embed Error] {e}")
            return None

    def _cosine(self, a, b):
        if not a or not b:
            return -1.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0 or norm_b == 0:
            return -1.0
        return dot / (norm_a * norm_b)

    def remember(self, subject: str, relation: str, value: str):
        subject, relation, value = subject.strip().lower(), relation.strip().lower(), value.strip()
        emb = self._embed(f"{subject} {relation}") if client else None

        conn = self._connect()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT OR IGNORE INTO facts (subject, relation, value, embedding)
                VALUES (?, ?, ?, ?)
            """, (subject, relation, value, emb))
            conn.commit()
            print(f"[SQLiteMemory] ✅ Remembered: {subject} → {relation}: {value}")
        except Exception as e:
            print(f"[SQLiteMemory] ⚠️ Insert failed: {e}")
        finally:
            conn.close()

    def recall(self, subject: str, relation: str):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT value FROM facts WHERE subject=? AND relation=?", (subject.lower(), relation.lower()))
        rows = [r[0] for r in cur.fetchall()]
        conn.close()
        return rows[0] if len(rows) == 1 else rows or None

    def search(self, query: str):
        conn = self._connect()
        cur = conn.cursor()
        q = f"%{query.lower()}%"
        cur.execute("SELECT subject, relation, value FROM facts WHERE relation LIKE ? OR value LIKE ?", (q, q))
        results = cur.fetchall()
        conn.close()
        if results:
            best = max(results, key=lambda x: SequenceMatcher(None, query, x[1]).ratio())
            return f"{best[0].title()}'s {best[1]} is {best[2]}"
        return None

    def semantic_search(self, query: str):
        if not client:
            return None
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT subject, relation, value, embedding FROM facts WHERE embedding IS NOT NULL")
        rows = cur.fetchall()
        conn.close()

        q_emb_resp = client.embeddings.create(model=EMBED_MODEL, input=query)
        q_emb = q_emb_resp.data[0].embedding

        best_score, best_row = 0.0, None
        for sub, rel, val, emb_json in rows:
            try:
                emb = json.loads(emb_json)
                score = self._cosine(q_emb, emb)
                if score > best_score:
                    best_score, best_row = score, (sub, rel, val)
            except Exception:
                continue

        if best_row and best_score >= 0.78:
            sub, rel, val = best_row
            print(f"[Semantic ✅] '{query}' → {rel} ({best_score:.2f})")
            return f"{sub.title()}'s {rel} is {val}"
        return None

    def export(self):
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT subject, relation, value FROM facts")
        rows = cur.fetchall()
        conn.close()
        data = {}
        for sub, rel, val in rows:
            data.setdefault(sub, {}).setdefault(rel, []).append(val)
        return data

    # ------------------------------
    # Legacy Compatibility Stubs
    # ------------------------------
    def sanitize_all(self):
        """Stub for legacy cleaner – not needed in SQLite version."""
        print("[SQLiteMemory] (stub) sanitize_all() skipped – SQLite handles this automatically.")

    @property
    def runtime_path(self):
        """Legacy JSON path reference – replaced by SQLite database."""
        return self.db_path


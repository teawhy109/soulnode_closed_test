import sqlite3
import json
import os
import math
from difflib import SequenceMatcher
from openai import OpenAI
import dotenv

# ------------------------------
# CONFIGURATION
# ------------------------------
# ✅ Load environment variables if .env exists
dotenv.load_dotenv()

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "memory_store.db")
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ✅ Load from environment or fallback (for local testing)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or "sk-proj-PASTE_YOUR_KEY_HERE"  # TEMP for local only
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")

client = None
if OPENAI_API_KEY and OPENAI_API_KEY.strip():
    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print(f"[SQLiteMemory] ✅ OpenAI client ready. Using model: {EMBED_MODEL}")
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
            print("[Embed ❌] Client missing or empty text.")
            return None
        try:
            print(f"[Embed 🚀] Creating embedding for: {text}")
            resp = client.embeddings.create(model=EMBED_MODEL, input=text)
            emb = resp.data[0].embedding
            print(f"[Embed ✅] Length: {len(emb)}")
            return json.dumps(emb)
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

        # 🧠 Use all 3 fields for embedding context
        emb = self._embed(f"{subject} {relation} {value}") if client else None
        if emb:
            print("[Embed ✅] Vector length:", len(json.loads(emb)))
        else:
            print("[Embed ⚠️] Embedding is None – check API key or OpenAI client")

        conn = self._connect()
        cur = conn.cursor()
        try:
            # UPSERT logic: if row exists, update embedding too
            cur.execute("""
                INSERT INTO facts (subject, relation, value, embedding)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(subject, relation, value) DO UPDATE SET embedding=excluded.embedding
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

        # normalize query to match how we embed facts
        normalized_q = query.lower().replace("’", "'").replace("whats", "what is").replace("ty’s", "ty").replace("ty's", "ty")
        q_emb_resp = client.embeddings.create(model=EMBED_MODEL, input=normalized_q)

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

        if best_row and best_score >= 0.55:
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
    
    def semantic_search(self, query: str):
        if not client:
            return None

        # 🧠 Flex Layer: normalize slang, punctuation, and phrasing aggressively
        normalized_q = query.lower().strip()
        normalized_q = normalized_q.replace("’", "'")
        normalized_q = normalized_q.replace("whats", "what is")
        normalized_q = normalized_q.replace("ty’s", "ty")
        normalized_q = normalized_q.replace("ty's", "ty")
        normalized_q = normalized_q.replace("ride", "car")
        normalized_q = normalized_q.replace("whip", "car")
        normalized_q = normalized_q.replace("vehicle", "car")
        normalized_q = normalized_q.replace("want most", "dream")
        normalized_q = normalized_q.replace("ultimate ride", "dream car")  # NEW 🔥
        normalized_q = normalized_q.replace("dream whip", "dream car")     # NEW 🔥

        # 🧠 Add “relation boosters” for more semantic weight
        boosted_query = (
            f"question: {normalized_q}. "
            f"keywords: dream, goal, desire, ultimate, main, favorite, most wanted."
        )

        # create query embedding
        q_emb_resp = client.embeddings.create(model=EMBED_MODEL, input=boosted_query)
        q_emb = q_emb_resp.data[0].embedding

        # get all facts with embeddings
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("SELECT subject, relation, value, embedding FROM facts WHERE embedding IS NOT NULL")
        rows = cur.fetchall()
        conn.close()

        best_score, best_row = 0.0, None
        for sub, rel, val, emb_json in rows:
            try:
                emb = json.loads(emb_json)
                score = self._cosine(q_emb, emb)
                if score > best_score:
                    best_score, best_row = score, (sub, rel, val)
            except Exception:
                continue

        # 🔥 FINAL THRESHOLD (aggressive recall mode)
        if best_row and best_score >= 0.45:
            sub, rel, val = best_row
            print(f"[Semantic ✅] '{query}' → {rel} ({best_score:.2f})")
            return f"{sub.title()}'s {rel} is {val}"

        print(f"[Semantic ❌] '{query}' → No strong match (best_score={best_score:.2f})")
        return None



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


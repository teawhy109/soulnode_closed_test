import sqlite3
import json
import os
from openai import OpenAI

# ✅ Load API key and model from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")

if not OPENAI_API_KEY:
    raise ValueError("❌ OPENAI_API_KEY is not set. Set it before running this script.")

client = OpenAI(api_key=OPENAI_API_KEY)

# ✅ Path to your DB (adjust if needed)
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "memory_store.db")

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# ✅ Fetch all rows missing embeddings
cur.execute("SELECT id, subject, relation, value FROM facts WHERE embedding IS NULL")
rows = cur.fetchall()

if not rows:
    print("✅ All facts already have embeddings — nothing to update.")
    conn.close()
    exit()

print(f"🚀 Found {len(rows)} rows without embeddings. Starting re-embed...")

updated = 0
for row in rows:
    _id, subject, relation, value = row
    text = f"{subject} {relation} {value}"

    try:
        print(f"[Embedding] ID={_id} → {text}")
        resp = client.embeddings.create(model=EMBED_MODEL, input=text)
        embedding_vector = resp.data[0].embedding
        cur.execute("UPDATE facts SET embedding = ? WHERE id = ?", (json.dumps(embedding_vector), _id))
        updated += 1

    except Exception as e:
        print(f"⚠️ Failed to embed row { _id }: {e}")

conn.commit()
conn.close()

print(f"✅ Done. Successfully updated {updated} rows with semantic embeddings.")

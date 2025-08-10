import json
import os
import tiktoken
from datetime import datetime

MEMORY_FILE_PATH = "memorystore.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE_PATH):
        return []
    with open(MEMORY_FILE_PATH, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def count_tokens(text):
    encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))

def rank_memories(memories, query):
    ranked = []
    for mem in memories:
        score = 0
        if "content" in mem:
            content = mem["content"].lower()
            q = query.lower()
            if q in content:
                score += 5
            score += sum(1 for word in q.split() if word in content)
            score -= abs(count_tokens(content) - count_tokens(query)) * 0.1
        mem["score"] = score
        ranked.append(mem)
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked

def get_ranked_memories(query, top_k=5):
    memories = load_memory()
    if not memories:
        return []

    ranked = rank_memories(memories, query)
    return ranked[:top_k]

# Example usage (for debugging only — remove in production)
if __name__ == "__main__":
    test_query = "health and fasting strategy"
    top_memories = get_ranked_memories(test_query)
    for mem in top_memories:
        print(mem)
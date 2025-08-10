# phase12_3_ranked_context_recall.py

from logic import load_session_memory

def recall_ranked_by_context(context_filter):
    print(f"\n--- SoulNode Entries in Context: {context_filter.upper()} (Ranked by Importance) ---")

    # Load session memory data
    memory_data = load_session_memory('Session_Memory.json')

    # Filter by matching context
    filtered = [entry for entry in memory_data if entry.get('context') == context_filter]

    # Sort by importance descending (5 = most important)
    sorted_entries = sorted(filtered, key=lambda e: int(e.get('importance', 0)), reverse=True)

    for entry in sorted_entries:
        print(f"- [{entry['tone'].capitalize()}] {entry['user_input']} (Importance: {entry['importance']})")

    print(f"\nTotal Entries Found: {len(sorted_entries)}")

if __name__ == "__main__":
    print("\n--- SoulNode Ranked Context Recall ---")
    context = input("Enter context to rank recall (e.g. mindset, health, family): ")
    recall_ranked_by_context(context)
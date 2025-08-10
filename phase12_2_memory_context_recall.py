import json

def load_session_memory(filepath):
    try:
        with open(filepath, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def recall_by_context(context_filter):
    memory_path = "SoulNodeMemory.json"
    memory_data = load_session_memory(memory_path)

    matches = [
        entry for entry in memory_data
        if entry.get("context", "").lower() == context_filter.lower()
    ]

    if not matches:
        print(f"No entries found under context: {context_filter}")
        return

    print(f"\n--- Entries Tagged '{context_filter.upper()}' ---")
    for entry in matches:
        if all(k in entry for k in ("tone", "input", "importance")):
            print(f"- [{entry['tone'].capitalize()}] {entry['input']} (Importance: {entry['importance']})")
        else:
            print(f"- Skipped: \"{entry.get('user_input', 'No input found')}\" — missing tone or importance.")

    print(f"\nTotal Entries Found: {len(matches)}")

if __name__ == "__main__":
    print("---- SoulNode Context Recall ----")
    context = input("Enter context to recall (e.g. mindset, health, family): ")
    recall_by_context(context)
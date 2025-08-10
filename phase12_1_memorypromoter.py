import json
from datetime import datetime

MEMORY_FILE = "SoulNodeMemory.json"

def promote_memory_entry(user_input, tone, context, importance):
    try:
        with open(MEMORY_FILE, "r") as file:
            memory_data = json.load(file)
    except FileNotFoundError:
        memory_data = []

    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "tone": tone,
        "context": context,
        "importance": importance
    }

    memory_data.append(entry)

    with open(MEMORY_FILE, "w") as file:
        json.dump(memory_data, file, indent=4)

    return "Memory entry promoted successfully."

# Example usage:
if __name__ == "__main__":
    print("---- SoulNode Memory Entry Promoter ----")
    user_input = input("Enter message to promote: ")
    tone = input("Enter tone (e.g. heart, chill, beast): ")
    context = input("Enter context category (e.g. health, mindset, family): ")
    importance = input("Enter importance level (1–5): ")

    result = promote_memory_entry(user_input, tone, context, importance)
    print(result)
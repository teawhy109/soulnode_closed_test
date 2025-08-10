import json
import os

MEMORY_FILE = "memory_store.json"

def fetch_contextual_memories(user_input, user_profile):
    try:
        if not os.path.exists(MEMORY_FILE):
            return []

        with open(MEMORY_FILE, "r") as file:
            memory_data = json.load(file)

        user_name = user_profile.get("name", "Unknown").lower()
        relevant = []

        for entry in reversed(memory_data): # reverse = most recent first
            if user_name in entry.get("user", "").lower():
                if any(keyword in entry.get("input", "").lower() for keyword in user_input.lower().split()):
                    relevant.append(entry)
                elif any(keyword in entry.get("response", "").lower() for keyword in user_input.lower().split()):
                    relevant.append(entry)

            if len(relevant) >= 5:
                break

        return relevant

    except Exception as e:
        return [{"error": str(e)}]
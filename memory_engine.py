import json
import os

MEMORY_FILE = "memory_store.json"

def save_memory(user_input, response, user_profile):
    memory_entry = {
        "user_input": user_input,
        "response": response,
        "user_profile": user_profile
    }

    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            try:
                memory_data = json.load(f)
            except json.JSONDecodeError:
                memory_data = []
    else:
        memory_data = []

    memory_data.append(memory_entry)

    with open(MEMORY_FILE, "w") as f:
        json.dump(memory_data, f, indent=2)
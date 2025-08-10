import json
import os

MEMORY_FILE = "memory_store.json"
UNKNOWN_FILE = "unknown_inputs.json"

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

def load_memory():
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            try:
                memory_data = json.load(f)
                return json.dumps(memory_data, indent=2)
            except json.JSONDecodeError:
                return "Memory file exists but is corrupted."
    else:
        return "No memory has been logged yet."

def log_unknown_input(user_input, memory_data, user_profile):
    entry = {
        "user_input": user_input,
        "response": "Commander Ty, I'm not sure how to respond to that yet, but I've logged it to learn from.",
        "user_profile": user_profile
    }

    if os.path.exists(UNKNOWN_FILE):
        with open(UNKNOWN_FILE, "r") as f:
            try:
                unknown_data = json.load(f)
            except json.JSONDecodeError:
                unknown_data = []
    else:
        unknown_data = []

    unknown_data.append(entry)

    with open(UNKNOWN_FILE, "w") as f:
        json.dump(unknown_data, f, indent=2)

    return entry
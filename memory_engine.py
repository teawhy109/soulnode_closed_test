import json
import os

MEMORY_FILE = "core_memory.json"

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        return {}
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

def remember_user(user_id, user_message, assistant_response):
    memory = load_memory()
    if user_id not in memory:
        memory[user_id] = []
    memory[user_id].append({
        "user": user_message,
        "assistant": assistant_response
    })
    save_memory(memory)

def get_last_interaction(user_id):
    memory = load_memory()
    if user_id in memory and memory[user_id]:
        return memory[user_id][-1]
    return None

def save_interaction(user_id, message, response):
    try:
        if os.path.exists("memory_store.json"):
            with open("memory_store.json", "r") as file:
                memory = json.load(file)
        else:
            memory = {}

        if user_id not in memory:
            memory[user_id] = {"interactions": []}

        memory[user_id]["interactions"].append({
            "message": message,
            "response": response
        })

        with open("memory_store.json", "w") as file:
            json.dump(memory, file, indent=4)

    except Exception as e:
        print(f"Error saving interaction: {e}")
def get_recent_memories(user_id, limit=3):
    try:
        with open("memory_store.json", "r") as file:
            memory = json.load(file)
        if user_id in memory and "interactions" in memory[user_id]:
            return memory[user_id]["interactions"][-limit:]
        else:
            return []
    except Exception as e:
        print(f"Error retrieving recent memories: {e}")
        return []
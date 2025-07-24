import json
import os

MEMORY_FILE = "memorystore.json"

class SoulNodeMemory:

    def __init__(self):
        if not os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "w") as f:
                json.dump({}, f)

    def save_memory(self, data):
        with open(MEMORY_FILE, "w") as f:
            json.dump(data, f)

    def clear_memory(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump({}, f)

    def export_memory(self):
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, "r") as f:
                data = json.load(f)
                return data if data else {"message": "Memory is empty"}
        else:
            return {"error": "Memory file not found"}
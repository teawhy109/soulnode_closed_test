import json
import os

class SoulNodeMemory:
    def __init__(self):
        self.memory_log = []

    def save(self, input_text, response_text):
        self.memory_log.append({
            "input": input_text,
            "response": response_text
        })

    def clear(self):
        self.memory_log = []

    def export_txt(self, filename="soulnode_memory_export.txt"):
        with open(filename, "w", encoding="utf-8") as f:
            for entry in self.memory_log:
                f.write(f"Input: {entry['input']}\n")
                f.write(f"Response: {entry['response']}\n\n")

    def export_json(self, filename="soulnode_memory_export.json"):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.memory_log, f, indent=4, ensure_ascii=False)

    def load_json(self, filename="soulnode_memory_export.json"):
        if os.path.exists(filename):
            with open(filename, "r", encoding="utf-8") as f:
                self.memory_log = json.load(f)
        else:
            self.memory_log = []
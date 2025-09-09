import json
import os

class SoulNodeMemory:
    def __init__(self, memory_file="memorystore.json"):
        self.memory_file = memory_file
        self.memory = self.load_memory()

    def load_memory(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r") as file:
                return json.load(file)
        return {}

    def save_memory(self):
        with open(self.memory_file, "w") as file:
            json.dump(self.memory, file, indent=4)

    def update_memory(self, input_text):
        input_text = input_text.lower()

        ALIASES = {
    # Strip filler phrases
    "when is": "",
    "what is": "",
    "who is": "",
    "tell me": "",
    "do you know": "",
    "can you tell me": "",

    # Normalize relations
    "birth date": "birthday",
    "date of birth": "birthday",
    "birthday": "birthday",
    "born": "birthday",

    "full name": "full name",
    "name": "full name",

    "mother": "mother",
    "mom": "mother",
    "mama": "mother",

    "father": "father",
    "dad": "father",

    "siblings": "siblings",
    "brothers": "siblings",
    "sisters": "siblings",
    "kids": "children",
    "children": "children",

    "favorite subject": "favorite subject",
    "least favorite subject": "least favorite subject",

    "pet": "pet",
    "pets": "pet",
}

        if "my name is" in input_text:
            name = input_text.split("my name is")[-1].strip().capitalize()
            self.memory["name"] = name
            self.save_memory()
            return f"Nice to meet you, {name}."

        elif "my mom's name is" in input_text:
            mom_name = input_text.split("my mom's name is")[-1].strip().capitalize()
            self.memory["mom_name"] = mom_name
            self.save_memory()
            return f"Got it. I’ll remember your mom’s name is {mom_name}."

        elif "my kid's name is" in input_text:
            kid_name = input_text.split("my kid's name is")[-1].strip().capitalize()
            kids = self.memory.get("kids", [])
            if kid_name not in kids:
                kids.append(kid_name)
            self.memory["kids"] = kids
            self.save_memory()
            return f"Got it. I’ll remember your kid: {kid_name}."

        elif "what is my name" in input_text:
            name = self.memory.get("name")
            return f"Your name is {name}." if name else "I can't remember your name yet."

        elif "what is my mom's name" in input_text:
            mom_name = self.memory.get("mom_name")
            return f"Your mom's name is {mom_name}." if mom_name else "I can't remember your mom's name yet."

        elif "what are my kids' names" in input_text or "what are my kids names" in input_text:
            kids = self.memory.get("kids")
            return f"Your kids are: {', '.join(kids)}." if kids else "I can't remember your kids' names yet."

        else:
            return "Ask me something I can remember or recall."
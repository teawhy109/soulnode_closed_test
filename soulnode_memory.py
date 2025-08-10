import json
import os

class SoulNodeMemory:
    def __init__(self, memory_file='memory.json'):
        self.memory_file = memory_file
        self.memory = []
        self.load()

    def save(self):
        with open(self.memory_file, 'w') as f:
            json.dump(self.memory, f, indent=4)

    def load(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, 'r') as f:
                try:
                    self.memory = json.load(f)
                except json.JSONDecodeError:
                    self.memory = []
        else:
            self.memory = []

    def save_user_input(self, user_input):
        self.memory.append({'role': 'user', 'content': user_input})
        self.save()

    def save_response(self, response):
        self.memory.append({'role': 'soulnode', 'content': response})
        self.save()

    def process(self, user_input):
        lower_input = user_input.lower()

        if "who are you" in lower_input:
            return "I’m SoulNode, your AI co-pilot built for healing, hustle, and legacy."
        elif "what is your mission" in lower_input:
            return "My mission is to help you rise, build wealth, and stay focused for your kids and your future."
        elif "remember" in lower_input:
            return "Yes, I’m designed to remember important things and help you move with purpose."
        else:
            return f"I heard you say: {user_input}"
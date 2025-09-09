import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

file_path = "memorystore.json"
memories = []

# Load existing memories if the file exists
if os.path.exists(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            memories = json.load(f)
        except json.JSONDecodeError:
            memories = []

# Example memory to append (replace or modify as needed)
new_memory = {
    "role": "system",
    "content": "This is an example memory entry. Replace this with your actual memory logic."
}

# Add the new memory
memories.append(new_memory)

# Save updated memories
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(memories, f, indent=4)

print("Memory ingested successfully.")
import json

def save_memory_entry(user_input, response, tone, topic):
    entry = {
        "input": user_input,
        "response": response,
        "tone": tone,
        "topic": topic
    }

    try:
        with open("soulnode_memory.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.append(entry)

    with open("soulnode_memory.json", "w") as f:
        json.dump(data, f, indent=2)

    return f"Memory saved for input: {user_input}"
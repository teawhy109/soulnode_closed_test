import json
from datetime import datetime

def load_session_memory(file_path):
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def summarize_by_tone(memory_data):
    tone_insights = {}

    for entry in memory_data:
        tone = entry.get("tone")
        input_text = entry.get("user_input", "")
        importance = entry.get("importance", 0)

        if not tone or not input_text:
            continue

        if tone not in tone_insights:
            tone_insights[tone] = {
                "total_entries": 0,
                "keywords": set(),
                "sample_entry": input_text,
                "total_importance": 0
            }

        tone_insights[tone]["total_entries"] += 1
        tone_insights[tone]["total_importance"] += int(importance)

        words = input_text.split()
        tone_insights[tone]["keywords"].update(words)

        if importance == 5:
            tone_insights[tone]["sample_entry"] = input_text

    for tone in tone_insights:
        tone_insights[tone]["keywords"] = list(tone_insights[tone]["keywords"])

    return tone_insights

def promote_memory_entry(user_input, tone, context, importance):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "tone": tone.lower(),
        "context": context.lower(),
        "importance": int(importance)
    }

    try:
        with open("SessionMemory.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.append(entry)

    with open("SessionMemory.json", "w") as f:
        json.dump(data, f, indent=2)

    return "Memory entry promoted successfully."

def match_memory_by_tone_and_input(user_input, predicted_tone):
    try:
        with open("soulnode_memory.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

    matches = []
    for entry in data:
        if (
            predicted_tone.lower() in entry.get("tone", "").lower()
            or user_input.lower() in entry.get("user_input", "").lower()
        ):
            matches.append(entry)

    return matches

def summarize_responses_by_topic(topic):
    try:
        with open("response_map.json", "r") as f:
            summaries = json.load(f).get(topic, [])
    except (FileNotFoundError, json.JSONDecodeError):
        summaries = []

    if summaries:
        return f"Summary for '{topic}': {summaries[0]}"
    else:
        return f"No summary found for topic: {topic}"

def predict_tone(user_input):
    input_lower = user_input.lower()
    if "tired" in input_lower or "calm" in input_lower:
        return "Chill", "Detected 'tired' or 'calm' in input — Chill mode"
    elif "love" in input_lower or "purpose" in input_lower:
        return "Heart", "Detected 'love' or 'purpose' in input — Heart mode"
    else:
        return "Beast", "No specific trigger found. Defaulting to Beast tone."
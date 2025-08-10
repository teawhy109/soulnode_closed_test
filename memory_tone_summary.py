import json
import os

def load_session_memory(file_path):
    if not os.path.exists(file_path):
        return []
    with open(file_path, 'r') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def summarize_by_tone(memory_data):
    tone_summaries = {
        "chill": [],
        "heart": [],
        "beast": []
    }

    for entry in memory_data:
        tone = entry.get("tone", "").lower()
        message = entry.get("message", "")
        if tone in tone_summaries:
            tone_summaries[tone].append(message)

    tone_insights = {}
    for tone, messages in tone_summaries.items():
        if messages:
            total = len(messages)
            keywords = set()
            for msg in messages:
                for word in msg.lower().split():
                    if len(word) > 5:
                        keywords.add(word.strip(".,!?"))
            tone_insights[tone] = {
                "total_entries": total,
                "keywords": list(keywords)[:10],
                "sample_entry": messages[-1]
            }

    return tone_insights

def run_summary():
    memory_path = 'Session_Memory.json'
    memory_data = load_session_memory(memory_path)
    insights = summarize_by_tone(memory_data)

    for tone, data in insights.items():
        print(f"\nTone: {tone.upper()}")
        print(f"Total Entries: {data['total_entries']}")
        print(f"Common Keywords: {', '.join(data['keywords'])}")
        print(f"Most Recent Entry: {data['sample_entry']}")

if __name__ == "__main__":
    run_summary()
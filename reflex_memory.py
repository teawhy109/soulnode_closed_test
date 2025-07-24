# reflex_memory.py

conversation_history = []

def log_exchange(user_prompt, rene_reply):
    conversation_history.append({
        "user": user_prompt,
        "rene": rene_reply
    })

def get_recent_conversation(limit=5):
    return conversation_history[-limit:] if conversation_history else []

def summarize_thread():
    summary = ""
    for entry in get_recent_conversation():
        summary += f"User said: {entry['user']}\nRene replied: {entry['rene']}\n"
    return summary.strip()
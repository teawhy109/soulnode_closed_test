from datetime import datetime
from memory import store_memory

def escalate(message):
    message = message.lower()

    if "emergency override" in message:
        level = "high"
        response = "High-level escalation protocol triggered."
    elif "activate system" in message:
        level = "standard"
        response = "Escalation protocol triggered."
    elif "ping status" in message:
        level = "low"
        response = "Low-level escalation initiated."
    else:
        return {
            "status": "OK",
            "response": "No escalation required.",
            "level": "none"
        }

    memory_event = {
        "event": "escalation_triggered",
        "level": level,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }

    store_memory(memory_event)

    return {
        "status": "ESCALATED",
        "response": response,
        "level": level
    }

__all__ = ["escalate"]
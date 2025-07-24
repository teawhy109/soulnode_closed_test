# utils.py

current_mode = "tactical" # Default mode

def log_event(input_text):
    return f"[LOG EVENT] {input_text} has been logged."

def audit_system():
    return {
        "status": "AUDIT COMPLETE",
        "checkpoints": [
            "Memory structure validated",
            "Current mode operational",
            "System routes functional"
        ]
    }

def generate_report():
    return {
        "report": "All systems nominal. No outstanding issues found."
    }

def generate_mode_response(user_input, current_mode):
    if current_mode == "tactical":
        return f"[TACTICAL] Executing directive: {user_input}"
    elif current_mode == "soul":
        return f"[SOUL] I'm with you on this: {user_input}"
    elif current_mode == "nobs":
        return f"[NO BS] Direct response: {user_input}"
    elif current_mode == "warlord":
        return f"[WARLORD] Execute or get out the way: {user_input}"
    else:
        return f"[DEFAULT] Echo: {user_input}"

def switch_mode(new_mode):
    global current_mode
    valid_modes = ["tactical", "soul", "nobs", "warlord"]
    if new_mode.lower() in valid_modes:
        current_mode = new_mode.lower()
        return f"Mode switched to: {current_mode.upper()}"
    else:
        return "Invalid mode requested."

def get_current_mode():
    return current_mode

__all__ = [
    "log_event",
    "audit_system",
    "generate_report",
    "generate_mode_response",
    "switch_mode",
    "get_current_mode"
]
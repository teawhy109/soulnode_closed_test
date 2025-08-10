# phase11_9_feedback_audit.py

import json
from datetime import datetime

SESSION_FILE = "Session_Memory.json"
FEEDBACK_FILE = "tone_feedback_log.json"

def load_json(path):
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def audit_feedback_accuracy():
    feedback_data = load_json(FEEDBACK_FILE)
    audit_log = []

    for feedback in feedback_data:
        user_input = feedback.get("input", "")
        predicted_tone = feedback.get("predicted_tone", "")
        correct_tone = feedback.get("correct_tone", "")
        timestamp = feedback.get("timestamp", datetime.now().isoformat())

        status = "correct" if predicted_tone == correct_tone else "incorrect"

        audit_entry = {
            "input": user_input,
            "predicted_tone": predicted_tone,
            "correct_tone": correct_tone,
            "timestamp": timestamp,
            "status": status
        }

        audit_log.append(audit_entry)

    with open("Tone_Feedback_Audit.json", "w") as f:
        json.dump(audit_log, f, indent=2)

    print("Tone Feedback Audit Complete")
    print("Total Entries:", len(audit_log))
    print("Correct Predictions:", sum(1 for a in audit_log if a["status"] == "correct"))
    print("Incorrect Predictions:", sum(1 for a in audit_log if a["status"] == "incorrect"))

if __name__ == "__main__":
    audit_feedback_accuracy()
import gradio as gr
import json
from datetime import datetime

SESSION_LOG = "session_memory.json"

def recall_sessions(topic_filter="", from_date="", to_date=""):
    try:
        with open(SESSION_LOG, "r") as f:
            sessions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "Session log is empty or unreadable."

    results = []
    for entry in sessions:
        topic_match = topic_filter.lower() in entry.get("topic", "").lower()
        date_match = True

        if from_date:
            entry_time = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            if entry_time.date() < from_dt.date():
                date_match = False

        if to_date:
            entry_time = datetime.strptime(entry["timestamp"], "%Y-%m-%d %H:%M:%S")
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            if entry_time.date() > to_dt.date():
                date_match = False

        if topic_match and date_match:
            formatted = f"[{entry['timestamp']}] [{entry['tone'].upper()}] {entry['input']} → {entry['response']}"
            results.append(formatted)

    return "\n\n".join(results) if results else "No matching sessions found."

def launch_phase11_2():
    with gr.Blocks() as app:
        gr.Markdown("## SoulNode | Phase 11.2 – Recall Past Sessions")

        topic_input = gr.Textbox(label="Filter by Topic (optional)", placeholder="e.g. mindset")
        from_date = gr.Textbox(label="From Date (YYYY-MM-DD)", placeholder="2025-07-25")
        to_date = gr.Textbox(label="To Date (YYYY-MM-DD)", placeholder="2025-07-27")

        output = gr.Textbox(label="Matching Session Entries", lines=15)

        recall_button = gr.Button("Recall Sessions")

        recall_button.click(fn=recall_sessions, inputs=[topic_input, from_date, to_date], outputs=output)

    app.launch()

if __name__ == "__main__":
    launch_phase11_2()
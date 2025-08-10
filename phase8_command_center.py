import json
import gradio as gr

# SEARCH UNKNOWN INPUTS
def search_unknowns(query):
    try:
        with open("unknown_inputs.json", "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No unknown inputs found."

    results = [
        entry for entry in data
        if isinstance(entry, dict)
        and "user_input" in entry
        and query.lower() in entry["user_input"].lower()
    ]

    return json.dumps(results, indent=2)

# REPLAY FUNCTION (for future use, placeholder)
def replay_ui():
    return gr.Textbox(label="Replay UI not implemented yet")

# PROMOTION TRACKER FUNCTION (for future use, placeholder)
def promotion_tracker_ui():
    return gr.Textbox(label="Promotion Tracker UI not implemented yet")

# MEMORY SEARCH UI
def memory_search_ui():
    with gr.Row():
        query_input = gr.Textbox(label="Search Phrase", placeholder="e.g. glucose, setbacks, confidence")
        search_output = gr.Textbox(label="Search Results", lines=10)

    def run_search(query):
        return search_unknowns(query)

    search_btn = gr.Button("Search")
    search_btn.click(fn=run_search, inputs=query_input, outputs=search_output)

    return [query_input, search_btn, search_output]

# PHASE 8 COMMAND CENTER UI
def launch_phase8():
    with gr.Blocks(title="SoulNode Phase 8 Command Center") as app:
        gr.Markdown("# SoulNode | Phase 8.1 - 8.3 | Tactical Memory Interface")

        # Add Memory Search UI
        search_ui_elements = memory_search_ui()

        # Add Replay + Tracker placeholders
        replay_output = replay_ui()
        tracker_output = promotion_tracker_ui()

    app.launch()

# RUN APP
if __name__ == "__main__":
    launch_phase8()
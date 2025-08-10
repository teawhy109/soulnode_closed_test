import gradio as gr
import json

TAG_FILE = "soulnode_memory.json"

def recall_by_topic(tag):
    try:
        with open(TAG_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory data found."

    tag_lower = tag.lower()
    matches = []

    for entry in data:
        if entry.get("topic", "").lower() == tag_lower:
            match = f"TONE: {entry.get('tone', 'N/A')}\nRESPONSE: {entry.get('response', 'N/A')}\n"
            matches.append(match)

    if matches:
        return "\n\n".join(matches)
    else:
        return f"No entries found for topic: {tag}"

def launch_phase10_7():
    gr.Markdown("### SoulNode | Phase 10.7 – Recall All Entries by Topic Tag")

    with gr.Blocks() as app:
        with gr.Row():
            topic_input = gr.Textbox(label="Enter Topic Tag (e.g. motivation, glucose, dadmode)")
            results_output = gr.Textbox(label="All Matched Responses")

        search_btn = gr.Button("Recall All by Topic")
        search_btn.click(fn=recall_by_topic, inputs=topic_input, outputs=results_output)

    app.launch()

if __name__ == "__main__":
    launch_phase10_7()
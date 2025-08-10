import gradio as gr
import json
from voice_output import speak_text

TAG_FILE = "spoken_memory.json"

def recall_by_tag(tag):
    try:
        with open(TAG_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No spoken memory found."

    tag_lower = tag.lower()
    matches = [
        entry["response"]
        for entry in data
        if entry.get("topic", "").lower() == tag_lower
    ]

    if not matches:
        return "No entries found for this tag."

    for msg in matches:
        speak_text(msg)

    return "\n\n".join(matches)

def launch_phase9_7():
    with gr.Blocks(title="SoulNode | Phase 9.7 - Recall by Tag") as app:
        gr.Markdown("### SoulNode | Phase 9.7 - Recall Spoken Memory by Tag")

        with gr.Row():
            tag_input = gr.Textbox(label="Enter Topic Tag (e.g. motivation, glucose, dadmode)")
            tag_output = gr.Textbox(label="Matched Responses")

        recall_btn = gr.Button("Recall by Tag")
        recall_btn.click(fn=recall_by_tag, inputs=tag_input, outputs=tag_output)

    app.launch()

if __name__ == "__main__":
    launch_phase9_7()
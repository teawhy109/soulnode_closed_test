import gradio as gr
import json

TONE_FILE = "soulnode_memory.json"

def recall_by_tone(tone):
    try:
        with open(TONE_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory data found."

    tone_lower = tone.lower()
    matches = []

    for entry in data:
        if entry.get("tone", "").lower() == tone_lower:
            matches.append(entry["response"])

    if matches:
        return "\n\n".join(matches)
    else:
        return "No entries found for this tone."

def launch_phase10_4():
    with gr.Blocks(title="SoulNode | Phase 10.4 - Filter by Tone") as app:
        gr.Markdown("###  SoulNode | Filter Memory by Tone")

        with gr.Row():
            tone_input = gr.Textbox(label="Enter Tone (chill, heart, beast)")
            tone_output = gr.Textbox(label="Matched Responses")

        tone_btn = gr.Button("Filter by Tone")
        tone_btn.click(fn=recall_by_tone, inputs=tone_input, outputs=tone_output)

    app.launch()

if __name__ == "__main__":
    launch_phase10_4()
import gradio as gr
import json
from voice_output import speak_text

MEMORY_FILE = "soulnode_memory.json"

def recall_by_input(user_input):
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory file found or it's corrupted."

    matches = []
    for entry in data:
        if user_input.lower() in entry.get("input", "").lower():
            matches.append(entry)

    if not matches:
        return "No matches found for that input."

    output_strings = []
    for match in matches:
        response = match.get("response", "")
        tone = match.get("tone", "Chill")
        topic = match.get("topic", "Unknown")
        output_strings.append(f"[{tone.upper()}] {response} (Topic: {topic})")
        speak_text(response)

    return "\n\n".join(output_strings)

def launch_phase10_3():
    with gr.Blocks(title="SoulNode | Phase 10.3 - Recall Memory by Input") as app:
        gr.Markdown("###  SoulNode Memory Recall - Match by User Input")
        
        input_text = gr.Textbox(label="Enter Input Phrase")
        output_box = gr.Textbox(label="Matched Memory")

        recall_btn = gr.Button("Recall Memory")
        recall_btn.click(fn=recall_by_input, inputs=input_text, outputs=output_box)

    app.launch()

if __name__ == "__main__":
    launch_phase10_3()
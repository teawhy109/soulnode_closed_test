import gradio as gr
import json
from voice_output import speak_text

MEMORY_FILE = "soulnode_memory.json"

def override_recall(user_input, override_tone):
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "Memory file missing or corrupted."

    for entry in data:
        if user_input.lower() in entry.get("input", "").lower():
            response = entry.get("response", "")
            original_tone = entry.get("tone", "")
            topic = entry.get("topic", "")

            # Speak in override tone
            speak_text(response, override_tone.lower())

            return f"OVERRIDE TONE: {override_tone.upper()}\nRESPONSE: {response}\nTOPIC: {topic}\nORIGINAL TONE: {original_tone}"

    return "No match found."

def launch_phase10_5():
    with gr.Blocks(title="SoulNode | Phase 10.5 - Override Tone Test") as app:
        gr.Markdown("### SoulNode | Dynamic Tone Redirection")

        input_text = gr.Textbox(label="User Input")
        override_tone = gr.Textbox(label="Override Tone (chill, heart, beast)")
        output_box = gr.Textbox(label="Response Output")

        recall_btn = gr.Button("Recall with Override Tone")
        recall_btn.click(fn=override_recall, inputs=[input_text, override_tone], outputs=output_box)

    app.launch()

if __name__ == "__main__":
    launch_phase10_5()
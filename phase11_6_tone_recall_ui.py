import gradio as gr
import json

SESSION_FILE = "session_memory.json"

def recall_by_tone(tone_input):
    try:
        with open(SESSION_FILE, "r") as f:
            sessions = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No session memory found."

    tone_input = tone_input.strip().lower()
    filtered = []

    for entry in sessions:
        if entry.get("tone", "").lower() == tone_input:
            formatted = (
                f"[{entry['timestamp']}] ({entry['tone'].upper()})\n"
                f"{entry['input']} → {entry['explanation']}"
            )
            filtered.append(formatted)

    return "\n\n".join(filtered) if filtered else f"No entries found for tone: {tone_input}"

def launch_phase11_6():
    with gr.Blocks() as app:
        gr.Markdown("## SoulNode | Phase 11.6 – Recall by Tone")

        tone_input = gr.Textbox(label="Enter Tone (Chill, Heart, or Beast)")
        results = gr.Textbox(label="Matching Sessions", lines=12)

        run_btn = gr.Button("Recall")

        run_btn.click(fn=recall_by_tone, inputs=tone_input, outputs=results)

    app.launch()

if __name__ == "__main__":
    launch_phase11_6()
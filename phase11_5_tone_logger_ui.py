import gradio as gr
import json
from datetime import datetime
from logic import predict_tone

SESSION_FILE = "session_memory.json"

def log_tone_session(user_input):
    tone, explanation = predict_tone(user_input)

    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "input": user_input,
        "tone": tone,
        "explanation": explanation
    }

    try:
        with open(SESSION_FILE, "r") as f:
            session_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        session_data = []

    session_data.append(entry)

    with open(SESSION_FILE, "w") as f:
        json.dump(session_data, f, indent=2)

    return f"Tone: {tone}\n\nExplanation: {explanation}\n\nLogged at {entry['timestamp']}"

def launch_phase11_5():
    with gr.Blocks() as app:
        gr.Markdown("## SoulNode | Phase 11.5 - Tone-Aware Session Logger")

        user_input = gr.Textbox(label="Enter Message", lines=3)
        result = gr.Textbox(label="Prediction & Log Result", lines=10)

        run_btn = gr.Button("Analyze & Log")

        run_btn.click(fn=log_tone_session, inputs=user_input, outputs=result)

    app.launch()

if __name__ == "__main__":
    launch_phase11_5()
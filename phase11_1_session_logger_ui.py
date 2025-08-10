import gradio as gr
import json
import uuid
import datetime

SESSION_LOG = "session_memory.json"

def predict_tone_v11(input_text):
    input_lower = input_text.lower()
    if "love" in input_lower or "peace" in input_lower:
        return "Heart"
    elif "tired" in input_lower or "calm" in input_lower:
        return "Chill"
    else:
        return "Beast"

def log_session_entry(user_input, response, tone, topic="general", correction=False):
    session_id = str(uuid.uuid4())
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    entry = {
        "session_id": session_id,
        "timestamp": timestamp,
        "tone": tone,
        "topic": topic,
        "input": user_input,
        "response": response,
        "corrected": correction
    }

    try:
        with open(SESSION_LOG, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = []

    data.append(entry)

    with open(SESSION_LOG, "w") as f:
        json.dump(data, f, indent=4)

    return f"Logged at {timestamp} under tone '{tone}' and topic '{topic}'."

def handle_input(user_input, topic_tag):
    tone = predict_tone_v11(user_input)

    # Placeholder response (simulate what SoulNode would say)
    if tone == "Heart":
        response = "You matter. Breathe. You're enough."
    elif tone == "Chill":
        response = "Let’s slow it down. You’ve got this."
    else:
        response = "Command your energy. Cut the noise. Lock in."

    log_result = log_session_entry(user_input, response, tone, topic_tag)
    return response, log_result

def launch_phase11_1():
    with gr.Blocks() as app:
        gr.Markdown("## SoulNode | Phase 11.1 – Session Memory Logger")

        input_text = gr.Textbox(label="What do you want to ask SoulNode?")
        topic_input = gr.Textbox(label="Optional Topic Tag", placeholder="e.g. focus, health, business")

        output_response = gr.Textbox(label="SoulNode’s Response")
        log_output = gr.Textbox(label="Logger Status")

        ask_button = gr.Button("Ask & Log")

        ask_button.click(fn=handle_input, inputs=[input_text, topic_input], outputs=[output_response, log_output])

    app.launch()

if __name__ == "__main__":
    launch_phase11_1()
import gradio as gr
import json

MEMORY_FILE = "soulnode_memory.json"

def predict_and_recall(user_input):
    try:
        with open(MEMORY_FILE, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return "No memory available."

    for entry in data:
        if user_input.lower() in entry["input"].lower() or entry["input"].lower() in user_input.lower():
            predicted_tone = entry["tone"]
            response = entry["response"]
            topic = entry.get("topic", "N/A")
            return f"TONE: {predicted_tone}\nRESPONSE: {response}\nTOPIC: {topic}"

    return "No memory match found for predicted tone."

def launch_phase10_6():
    with gr.Blocks(title="SoulNode | Phase 10.6 – Tone Memory Predictor") as app:
        gr.Markdown("###  SoulNode | Phase 10.6 – Predict Tone & Recall Response")

        user_input = gr.Textbox(label="Your Command")
        output = gr.Textbox(label="Predicted Response")

        predict_btn = gr.Button("Predict and Recall")
        predict_btn.click(fn=predict_and_recall, inputs=user_input, outputs=output)

        app.launch()

if __name__ == "__main__":
    launch_phase10_6()
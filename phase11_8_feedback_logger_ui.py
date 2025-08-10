import gradio as gr
from logic import predict_tone

FEEDBACK_FILE = "tone_feedback_log.json"

def log_feedback(user_input, predicted_tone, correct_tone):
    import json
    try:
        with open(FEEDBACK_FILE, "r") as f:
            feedback_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        feedback_data = []

    feedback_entry = {
        "input": user_input,
        "predicted_tone": predicted_tone,
        "correct_tone": correct_tone
    }
    feedback_data.append(feedback_entry)

    with open(FEEDBACK_FILE, "w") as f:
        json.dump(feedback_data, f, indent=2)

    return f"Logged correction: {predicted_tone} ➡ {correct_tone}"

def launch_phase11_8():
    with gr.Blocks() as app:
        gr.Markdown("## Phase 11.8 – Tone Intelligence Feedback Logger")

        user_input = gr.Textbox(label="User Input")
        predicted = gr.Textbox(label="Predicted Tone", interactive=False)
        correct_tone = gr.Radio(choices=["Chill", "Heart", "Beast"], label="Correct Tone (if different)")
        feedback_output = gr.Textbox(label="Feedback Log", interactive=False)

        def process_feedback(text, tone_override):
            predicted_tone = predict_tone(text)
            result = f"Prediction: {predicted_tone}"
            if predicted_tone != tone_override:
                correction = log_feedback(text, predicted_tone, tone_override)
                return predicted_tone, correction
            else:
                return predicted_tone, "Prediction was correct. No feedback logged."

        run_btn = gr.Button("Run Tone Prediction & Log Feedback")
        run_btn.click(fn=process_feedback, inputs=[user_input, correct_tone], outputs=[predicted, feedback_output])

    app.launch()

if __name__ == "__main__":
    launch_phase11_8()
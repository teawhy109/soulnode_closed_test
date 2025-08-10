import gradio as gr
import json
from logic import predict_tone

def launch_phase11_3():
    with gr.Blocks() as app:
        gr.Markdown("## SoulNode | Phase 11.3 - Contextual Tone Prediction")

        input_text = gr.Textbox(label="Your Input")

        predicted_tone = gr.Textbox(label="Predicted Tone")
        explanation = gr.Textbox(label="Reasoning")

        run_btn = gr.Button("Predict Tone")

        def predict_and_explain(user_input):
            tone, reason = predict_tone(user_input)
            return tone, reason

        run_btn.click(fn=predict_and_explain, inputs=input_text, outputs=[predicted_tone, explanation])

    app.launch()

if __name__ == "__main__":
    launch_phase11_3()
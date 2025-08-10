import gradio as gr
from voice_engine import speak_tone_response

def handle_speech(message, tone):
    if message.strip() == "":
        return "Please enter a message."
    speak_tone_response(message, tone)
    return f"Spoken in {tone.title()} Mode."

iface = gr.Interface(
    fn=handle_speech,
    inputs=[
        gr.Textbox(label="What should SoulNode say?"),
        gr.Dropdown(choices=["beast", "chill", "heart"], label="Choose Tone", value="chill")
    ],
    outputs="text",
    title="SoulNode Tone Selector",
    description="Choose a tone and enter a message to hear SoulNode speak it."
)

if __name__ == "__main__":
    iface.launch()
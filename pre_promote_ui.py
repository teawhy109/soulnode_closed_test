import gradio as gr
from voice_engine import speak_tone_response
import json
import os

MEMORY_STORE = "memorystore.json"

def load_memory():
    if os.path.exists(MEMORY_STORE):
        with open(MEMORY_STORE, "r") as f:
            return json.load(f)
    return []

def save_to_memory(entry):
    memory = load_memory()
    memory.append(entry)
    with open(MEMORY_STORE, "w") as f:
        json.dump(memory, f, indent=4)

def promote_input(message, tone, topic):
    if not message.strip():
        return "Message is empty."
    if not topic.strip():
        return "Topic tag is empty."

    # Speak the message in selected tone
    speak_tone_response(message, tone)

    # Save to memory
    memory_entry = {
        "topic": topic,
        "tone": tone,
        "message": message
    }
    save_to_memory(memory_entry)

    return f"Saved & spoken in {tone.title()} mode under topic: {topic}"

iface = gr.Interface(
    fn=promote_input,
    inputs=[
        gr.Textbox(label="What should SoulNode say?"),
        gr.Dropdown(choices=["beast", "chill", "heart"], label="Choose Tone", value="chill"),
        gr.Textbox(label="Memory Topic Tag (e.g. glucose, motivation, dadmode)")
    ],
    outputs="text",
    title="SoulNode Pre-Promote Customizer",
    description="Speak a message with tone and save it to memory with a topic tag."
)

if __name__ == "__main__":
    iface.launch()
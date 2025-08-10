import gradio as gr
from soulnode_memory import SoulNodeMemory

memory = SoulNodeMemory()

def chat_with_sono(user_input):
    lowered = user_input.lower()

    # Save memory if input is a known format
    if any(trigger in lowered for trigger in [
        "my name is", 
        "my mom's name is", 
        "my dad's name is", 
        "my kid's name is"
    ]):
        return memory.remember(user_input)

    # Recall memory if input is a question
    elif any(trigger in lowered for trigger in [
        "what is my name", 
        "who am i",
        "what is my mom's name", 
        "who is my mom",
        "what is my dad's name", 
        "who is my dad",
        "what is my kid's name", 
        "who is my kid"
    ]):
        return memory.recall(user_input)

    return "Ask me something I can remember or recall."

# Launch the UI
ui = gr.Interface(
    fn=chat_with_sono,
    inputs="text",
    outputs="text",
    title="SoNo AI System",
    description="Ask anything. If I don’t know, I’ll learn it.",
)

if __name__ == "__main__":
    ui.launch()